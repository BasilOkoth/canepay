from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            profile = getattr(request.user, "profile", None)
            if not profile or profile.role not in roles:
                messages.error(request, "You do not have access to that workspace.")
                return redirect("home")
            return view(request, *args, **kwargs)
        return wrapped
    return decorator
