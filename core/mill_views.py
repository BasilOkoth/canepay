from decimal import Decimal

from django.db.models import Sum
from django.shortcuts import render

from .decorators import role_required
from .models import Delivery, Mill, Receivable


def mill_queryset_for_user(user):
    """Return the verified mill record linked to the signed-in mill user's organisation."""
    profile = getattr(user, "profile", None)
    organisation = (getattr(profile, "organisation", "") or "").strip()
    if not organisation:
        return Mill.objects.none()
    return Mill.objects.filter(name=organisation)


@role_required("mill")
def mill_dashboard(request):
    """
    Miller workspace.

    Important: metrics are calculated on UNSLICED querysets. Django does not
    allow filter()/exclude() after a queryset has been sliced with [:100].
    Only the final rows sent to the template are limited to 100.
    """
    mills = mill_queryset_for_user(request.user)

    deliveries_qs = (
        Delivery.objects.filter(mill__in=mills)
        .select_related("farmer__user", "farm", "mill")
        .order_by("-delivered_at")
    )
    receivables_qs = (
        Receivable.objects.filter(delivery__mill__in=mills)
        .select_related(
            "delivery",
            "delivery__farmer__user",
            "delivery__mill",
            "assignment",
        )
        .order_by("-created_at")
    )

    metrics = {
        "outstanding": (
            receivables_qs.exclude(status__in=["settled", "cancelled"])
            .aggregate(v=Sum("amount"))["v"]
            or Decimal("0")
        ),
        "finance_linked": (
            receivables_qs.filter(status="financed")
            .aggregate(v=Sum("amount"))["v"]
            or Decimal("0")
        ),
        "pending_verification": deliveries_qs.filter(status="pending").count(),
    }

    context = {
        "deliveries": deliveries_qs[:100],
        "receivables": receivables_qs[:100],
        "metrics": metrics,
    }
    return render(request, "core/mill_dashboard.html", context)
