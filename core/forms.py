from django import forms
from .models import Delivery, FinanceOffer

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ["farmer","farm","mill","delivery_ticket_number","delivered_at","gross_weight_tonnes","accepted_weight_tonnes","quality_score","price_per_tonne","deductions"]
        widgets = {"delivered_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}
        labels = {
            "quality_score": "Quality / sucrose score",
            "price_per_tonne": "Price per tonne (KES)",
            "deductions": "Approved deductions (KES)",
        }
    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["delivery_ticket_number"].required = False
        if user and getattr(getattr(user, "profile", None), "role", None) == "mill":
            org = user.profile.organisation
            if org:
                self.fields["mill"].queryset = self.fields["mill"].queryset.filter(name=org)

class FinanceRequestForm(forms.Form):
    requested_amount = forms.DecimalField(min_value=1, decimal_places=2, max_digits=12, label="Amount you want now (KES)")
    consent_to_share = forms.BooleanField(label="I consent to share this verified delivery and mill obligation with participating banks and SACCOs.")

class FinanceOfferForm(forms.ModelForm):
    class Meta:
        model = FinanceOffer
        fields = ["advance_amount","finance_cost"]
        labels = {"advance_amount":"Amount to pay farmer now (KES)","finance_cost":"Financing cost (KES)"}
    def clean(self):
        cleaned = super().clean()
        advance = cleaned.get("advance_amount")
        cost = cleaned.get("finance_cost")
        if advance is not None and cost is not None:
            cleaned["settlement_amount"] = advance + cost
        return cleaned
