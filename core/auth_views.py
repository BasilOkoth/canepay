from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .auth_forms import AccountCreationForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = AccountCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        profile = user.profile
        if profile.account_status == "active":
            messages.success(request, "Account created. Welcome to your Miwa360 workspace.")
            return redirect("home")
        messages.success(request, "Account created. Your institution is queued for verification.")
        return redirect("account_pending")

    return render(request, "registration/signup.html", {"form": form})


@login_required
def account_pending(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return redirect("logout")
    if profile.account_status == "active":
        return redirect("home")
    return render(request, "core/account_pending.html", {"profile": profile})
