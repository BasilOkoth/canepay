from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.db import transaction

from .models import Farmer, Profile


class MiwaAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or email",
        widget=forms.TextInput(attrs={"autofocus": True, "autocomplete": "username", "placeholder": "Username or email"}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password", "placeholder": "Password"}),
    )

    def clean(self):
        identifier = self.cleaned_data.get("username")
        if identifier and "@" in identifier:
            matches = User.objects.filter(email__iexact=identifier)
            if matches.count() == 1:
                self.cleaned_data["username"] = matches.first().username
        return super().clean()


class AccountCreationForm(UserCreationForm):
    ROLE_CHOICES = [
        ("farmer", "Farmer"),
        ("mill", "Miller"),
        ("financier", "Bank / SACCO"),
    ]

    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone = forms.CharField(max_length=30)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    organisation = forms.CharField(max_length=160, required=False)
    national_id = forms.CharField(max_length=40, required=False, label="National ID / passport")
    farmer_number = forms.CharField(max_length=40, required=False, label="Farmer / grower number")
    county = forms.CharField(max_length=80, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "phone",
            "username",
            "role",
            "organisation",
            "national_id",
            "farmer_number",
            "county",
            "password1",
            "password2",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "first_name": "First name",
            "last_name": "Last name",
            "email": "you@example.com",
            "phone": "+254 7XX XXX XXX",
            "username": "Choose a username",
            "organisation": "Mill, bank or SACCO name",
            "national_id": "National ID / passport",
            "farmer_number": "Grower / farmer number",
            "county": "County",
            "password1": "Create password",
            "password2": "Confirm password",
        }
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("placeholder", placeholders.get(name, field.label))
            field.widget.attrs.setdefault("autocomplete", "off")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        if role == "farmer":
            for field_name in ("national_id", "farmer_number", "county"):
                if not cleaned.get(field_name):
                    self.add_error(field_name, "This field is required for a farmer account.")
        elif role in {"mill", "financier"} and not cleaned.get("organisation"):
            self.add_error("organisation", "Organisation name is required for institutional accounts.")
        return cleaned

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"].strip()
        user.last_name = self.cleaned_data["last_name"].strip()
        user.email = self.cleaned_data["email"].strip().lower()
        if not commit:
            return user

        user.save()
        role = self.cleaned_data["role"]
        status = "active" if role == "farmer" else "pending"
        Profile.objects.create(
            user=user,
            role=role,
            organisation=self.cleaned_data.get("organisation", "").strip(),
            phone=self.cleaned_data["phone"].strip(),
            account_status=status,
        )
        if role == "farmer":
            Farmer.objects.create(
                user=user,
                national_id=self.cleaned_data["national_id"].strip(),
                farmer_number=self.cleaned_data["farmer_number"].strip(),
                county=self.cleaned_data["county"].strip(),
                verified=False,
            )
        return user
