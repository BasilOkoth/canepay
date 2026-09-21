from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from core.auth_forms import MiwaAuthenticationForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(
            template_name="registration/login.html",
            authentication_form=MiwaAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("core.urls")),
]
