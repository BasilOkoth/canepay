from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Farmer, Profile


class AuthenticationUpgradeTests(TestCase):
    def test_farmer_can_create_real_account(self):
        response = self.client.post(reverse("signup"), {
            "first_name": "Akinyi",
            "last_name": "Otieno",
            "email": "akinyi@example.com",
            "phone": "+254700000111",
            "username": "akinyi",
            "role": "farmer",
            "organisation": "",
            "national_id": "ID-10001",
            "farmer_number": "GROWER-10001",
            "county": "Kisumu",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="akinyi")
        self.assertEqual(user.profile.role, "farmer")
        self.assertEqual(user.profile.account_status, "active")
        self.assertTrue(Farmer.objects.filter(user=user, farmer_number="GROWER-10001").exists())
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_financier_signup_is_pending_but_credentials_work(self):
        response = self.client.post(reverse("signup"), {
            "first_name": "Jane",
            "last_name": "Mwangi",
            "email": "jane@bank.example",
            "phone": "+254700000222",
            "username": "janebank",
            "role": "financier",
            "organisation": "Example SACCO",
            "national_id": "",
            "farmer_number": "",
            "county": "",
            "password1": "StrongPass123!",
            "password2": "StrongPass123!",
        })
        self.assertRedirects(response, reverse("account_pending"), fetch_redirect_response=False)
        user = User.objects.get(username="janebank")
        self.assertEqual(user.profile.account_status, "pending")
        protected = self.client.get(reverse("financier_dashboard"))
        self.assertRedirects(protected, reverse("account_pending"), fetch_redirect_response=False)

    def test_login_accepts_email_or_username(self):
        user = User.objects.create_user(username="realuser", email="real@example.com", password="StrongPass123!")
        Profile.objects.create(user=user, role="farmer", account_status="active")
        Farmer.objects.create(user=user, national_id="ID-20001", farmer_number="GROWER-20001", county="Kakamega", verified=False)

        response = self.client.post(reverse("login"), {"username": "real@example.com", "password": "StrongPass123!"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_pending_institution_can_be_activated_by_admin_state_change(self):
        user = User.objects.create_user(username="milleruser", email="mill@example.com", password="StrongPass123!")
        profile = Profile.objects.create(user=user, role="mill", organisation="Example Mill", account_status="pending")
        self.client.force_login(user)
        self.assertRedirects(self.client.get(reverse("mill_dashboard")), reverse("account_pending"), fetch_redirect_response=False)
        profile.account_status = "active"
        profile.save(update_fields=["account_status"])
        response = self.client.get(reverse("mill_dashboard"))
        self.assertEqual(response.status_code, 200)
