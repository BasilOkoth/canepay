from datetime import timedelta
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .decorators import role_required
from .forms import DeliveryForm, FinanceOfferForm, FinanceRequestForm
from .models import AuditEvent, Delivery, Farmer, FinanceOffer, FinanceRequest, Mill, Receivable, ReceivableAssignment, Settlement


def audit(user, event_type, obj, description):
    AuditEvent.objects.create(
        actor=user if getattr(user, "is_authenticated", False) else None,
        event_type=event_type,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        description=description,
    )

@login_required
def home(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return render(request, "core/no_role.html")
    return redirect(f"{profile.role}_dashboard")

@role_required("farmer")
def farmer_dashboard(request):
    farmer = get_object_or_404(Farmer, user=request.user)
    receivables = Receivable.objects.filter(delivery__farmer=farmer).select_related("delivery", "delivery__mill").order_by("-created_at")
    return render(request, "core/farmer_dashboard.html", {"farmer": farmer, "receivables": receivables})

@role_required("mill")
def mill_dashboard(request):
    mill_name = request.user.profile.organisation
    mills = Mill.objects.filter(name=mill_name) if mill_name else Mill.objects.all()
    deliveries = Delivery.objects.filter(mill__in=mills).select_related("farmer__user", "farm", "mill").order_by("-delivered_at")[:100]
    receivables = Receivable.objects.filter(delivery__mill__in=mills).select_related("delivery", "delivery__farmer__user", "delivery__mill").order_by("-created_at")[:100]
    return render(request, "core/mill_dashboard.html", {"deliveries": deliveries, "receivables": receivables})

@role_required("mill")
def delivery_create(request):
    if request.method == "POST":
        form = DeliveryForm(request.POST)
        if form.is_valid():
            delivery = form.save()
            audit(request.user, "delivery_created", delivery, f"Delivery {delivery.reference} created.")
            messages.success(request, "Delivery created.")
            return redirect("mill_dashboard")
    else:
        form = DeliveryForm(initial={"delivered_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")})
    return render(request, "core/form.html", {"form": form, "title": "Register cane delivery", "button": "Save delivery"})

@role_required("mill")
@transaction.atomic
def verify_delivery(request, pk):
    delivery = get_object_or_404(Delivery, pk=pk)
    if request.method == "POST":
        delivery.status = "verified"
        delivery.verified_by = request.user
        delivery.verified_at = timezone.now()
        delivery.save()
        receivable, _ = Receivable.objects.get_or_create(
            delivery=delivery,
            defaults={
                "reference": f"CP-{delivery.id:06d}",
                "amount": delivery.amount_payable,
                "due_date": timezone.localdate() + timedelta(days=14),
                "status": "draft",
            },
        )
        receivable.amount = delivery.amount_payable
        receivable.save(update_fields=["amount"])
        audit(request.user, "delivery_verified", delivery, f"Delivery verified; payable amount KES {delivery.amount_payable:,.2f}.")
        messages.success(request, "Delivery verified and receivable prepared.")
    return redirect("mill_dashboard")

@role_required("mill")
@transaction.atomic
def acknowledge_receivable(request, pk):
    receivable = get_object_or_404(Receivable.objects.select_related("delivery"), pk=pk)
    if request.method == "POST":
        receivable.mill_acknowledged = True
        receivable.acknowledged_by = request.user
        receivable.acknowledged_at = timezone.now()
        receivable.status = "verified"
        receivable.save()
        receivable.delivery.status = "acknowledged"
        receivable.delivery.save(update_fields=["status"])
        audit(request.user, "receivable_acknowledged", receivable, f"Mill acknowledged obligation of KES {receivable.amount:,.2f}.")
        messages.success(request, "Payment obligation acknowledged. Receivable is now financeable.")
    return redirect("mill_dashboard")

@role_required("farmer")
@transaction.atomic
def request_finance(request, pk):
    farmer = get_object_or_404(Farmer, user=request.user)
    receivable = get_object_or_404(Receivable, pk=pk, delivery__farmer=farmer, mill_acknowledged=True)
    if hasattr(receivable, "finance_request"):
        messages.info(request, "A financing request already exists for this receivable.")
        return redirect("farmer_dashboard")
    if request.method == "POST":
        form = FinanceRequestForm(request.POST)
        if form.is_valid():
            requested = form.cleaned_data["requested_amount"]
            if requested > receivable.amount:
                form.add_error("requested_amount", "Requested amount cannot exceed the receivable value.")
            else:
                fr = FinanceRequest.objects.create(
                    receivable=receivable,
                    farmer=farmer,
                    requested_amount=requested,
                    consent_to_share=form.cleaned_data["consent_to_share"],
                )
                receivable.status = "finance_requested"
                receivable.save(update_fields=["status"])
                audit(request.user, "finance_requested", fr, f"Farmer requested KES {requested:,.2f} financing.")
                messages.success(request, "Financing request submitted to participating financiers.")
                return redirect("farmer_dashboard")
    else:
        form = FinanceRequestForm(initial={"requested_amount": receivable.amount})
    return render(request, "core/form.html", {"form": form, "title": f"Finance {receivable.reference}", "button": "Request financing"})

@role_required("financier")
def financier_dashboard(request):
    requests = FinanceRequest.objects.filter(status="open", consent_to_share=True, receivable__mill_acknowledged=True).select_related("farmer__user", "receivable__delivery__mill", "receivable__delivery")
    my_offers = FinanceOffer.objects.filter(financier=request.user).select_related("request__receivable").order_by("-created_at")
    return render(request, "core/financier_dashboard.html", {"requests": requests, "my_offers": my_offers})

@role_required("financier")
def make_offer(request, pk):
    fr = get_object_or_404(FinanceRequest, pk=pk, status="open", consent_to_share=True)
    if request.method == "POST":
        form = FinanceOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.request = fr
            offer.financier = request.user
            offer.settlement_amount = form.cleaned_data["advance_amount"] + form.cleaned_data["finance_cost"]
            if offer.advance_amount > fr.requested_amount or offer.settlement_amount > fr.receivable.amount:
                form.add_error(None, "Offer cannot exceed the farmer request or receivable value.")
            else:
                offer.save()
                audit(request.user, "finance_offer_created", offer, f"Offer: advance KES {offer.advance_amount:,.2f}, cost KES {offer.finance_cost:,.2f}.")
                messages.success(request, "Financing offer submitted.")
                return redirect("financier_dashboard")
    else:
        suggested = (fr.requested_amount * Decimal("0.95")).quantize(Decimal("0.01"))
        form = FinanceOfferForm(initial={"advance_amount": suggested, "finance_cost": fr.receivable.amount - suggested})
    return render(request, "core/form.html", {"form": form, "title": f"Make offer for {fr.receivable.reference}", "button": "Submit offer"})

@role_required("farmer")
def receivable_detail(request, pk):
    farmer = get_object_or_404(Farmer, user=request.user)
    receivable = get_object_or_404(Receivable.objects.select_related("delivery", "delivery__mill"), pk=pk, delivery__farmer=farmer)
    offers = []
    if hasattr(receivable, "finance_request"):
        offers = receivable.finance_request.offers.select_related("financier", "financier__profile").order_by("advance_amount")
    events = AuditEvent.objects.filter(object_type__in=["Receivable", "FinanceRequest", "FinanceOffer", "Settlement"]).order_by("-created_at")[:50]
    return render(request, "core/receivable_detail.html", {"receivable": receivable, "offers": offers, "events": events})

@role_required("farmer")
@transaction.atomic
def accept_offer(request, pk):
    farmer = get_object_or_404(Farmer, user=request.user)
    offer = get_object_or_404(FinanceOffer.objects.select_related("request__receivable"), pk=pk, request__farmer=farmer, status="offered")
    if request.method == "POST":
        FinanceOffer.objects.filter(request=offer.request, status="offered").exclude(pk=offer.pk).update(status="declined")
        offer.status = "accepted"
        offer.accepted_at = timezone.now()
        offer.save()
        offer.request.status = "accepted"
        offer.request.save(update_fields=["status"])
        receivable = offer.request.receivable
        receivable.status = "financed"
        receivable.save(update_fields=["status"])
        ReceivableAssignment.objects.create(receivable=receivable, offer=offer, assigned_to=offer.financier)
        audit(request.user, "finance_offer_accepted", offer, f"Farmer accepted advance of KES {offer.advance_amount:,.2f}.")
        messages.success(request, "Offer accepted. The receivable has been assigned to the financier.")
    return redirect("receivable_detail", pk=offer.request.receivable.pk)

@role_required("financier")
def mark_disbursed(request, pk):
    offer = get_object_or_404(FinanceOffer, pk=pk, financier=request.user, status="accepted")
    if request.method == "POST":
        offer.status = "disbursed"
        offer.disbursed_at = timezone.now()
        offer.save()
        audit(request.user, "finance_disbursed", offer, f"Financier marked KES {offer.advance_amount:,.2f} as disbursed.")
        messages.success(request, "Disbursement recorded.")
    return redirect("financier_dashboard")

@role_required("mill")
@transaction.atomic
def settle_receivable(request, pk):
    receivable = get_object_or_404(Receivable, pk=pk)
    if request.method == "POST" and receivable.status != "settled":
        financier = receivable.assignment.assigned_to if hasattr(receivable, "assignment") else None
        Settlement.objects.create(receivable=receivable, financier=financier, amount_received=receivable.amount, reference=f"SET-{receivable.id:06d}")
        receivable.status = "settled"
        receivable.save(update_fields=["status"])
        receivable.delivery.status = "settled"
        receivable.delivery.save(update_fields=["status"])
        if hasattr(receivable, "finance_request"):
            receivable.finance_request.status = "closed"
            receivable.finance_request.save(update_fields=["status"])
        audit(request.user, "receivable_settled", receivable, f"Mill settlement of KES {receivable.amount:,.2f} recorded.")
        messages.success(request, "Settlement recorded and transaction closed.")
    return redirect("mill_dashboard")

@role_required("regulator")
def regulator_dashboard(request):
    totals = Receivable.objects.aggregate(total=Sum("amount"), count=Count("id"))
    unpaid = Receivable.objects.exclude(status="settled").aggregate(total=Sum("amount"), count=Count("id"))
    financed = Receivable.objects.filter(status="financed").aggregate(total=Sum("amount"), count=Count("id"))
    mills = Mill.objects.all()
    events = AuditEvent.objects.select_related("actor").all()[:100]
    return render(request, "core/regulator_dashboard.html", {"totals": totals, "unpaid": unpaid, "financed": financed, "mills": mills, "events": events})

@login_required
def api_receivable(request, reference):
    r = get_object_or_404(Receivable.objects.select_related("delivery__mill"), reference=reference)
    can_view = False
    role = getattr(getattr(request.user, "profile", None), "role", None)
    if role in {"mill", "financier", "regulator"}:
        can_view = True
    elif role == "farmer" and r.delivery.farmer.user_id == request.user.id:
        can_view = True
    if not can_view:
        return JsonResponse({"detail": "forbidden"}, status=403)
    return JsonResponse({
        "reference": r.reference,
        "valid": r.mill_acknowledged,
        "amount": str(r.amount),
        "mill": r.delivery.mill.name,
        "status": r.status,
        "already_financed": hasattr(r, "assignment") and r.assignment.active,
        "due_date": r.due_date.isoformat(),
    })
