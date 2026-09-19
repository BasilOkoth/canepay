from django import forms
from .models import Delivery, FinanceOffer

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ["reference", "farmer", "farm", "mill", "delivered_at", "gross_weight_tonnes", "accepted_weight_tonnes", "quality_score", "price_per_tonne", "deductions"]
        widgets = {"delivered_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

class FinanceRequestForm(forms.Form):
    requested_amount = forms.DecimalField(min_value=1, decimal_places=2, max_digits=12)
    consent_to_share = forms.BooleanField(label="I consent to share this verified receivable with participating financiers.")

class FinanceOfferForm(forms.ModelForm):
    class Meta:
        model = FinanceOffer
        fields = ["advance_amount", "finance_cost"]

    def clean(self):
        cleaned = super().clean()
        advance = cleaned.get("advance_amount")
        cost = cleaned.get("finance_cost")
        if advance is not None and cost is not None:
            cleaned["settlement_amount"] = advance + cost
        return cleaned
