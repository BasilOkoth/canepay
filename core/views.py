from datetime import timedelta
from decimal import Decimal, InvalidOperation
import json
import secrets
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .decorators import role_required
from .forms import DeliveryForm, FinanceOfferForm, FinanceRequestForm
from .models import (
    AuditEvent, Delivery, Farmer, Farm, FinanceOffer, FinanceRequest,
    IntegrationConnection, IntegrationEvent, Mill, Receivable,
    ReceivableAssignment, Settlement,
)

def audit(user, event_type, obj, description):
    AuditEvent.objects.create(
        actor=user if getattr(user, "is_authenticated", False) else None,
        event_type=event_type,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        description=description,
    )

def mill_queryset_for_user(user):
    org = getattr(getattr(user, "profile", None), "organisation", "")
    return Mill.objects.filter(name=org) if org else Mill.objects.none()

@login_required
def home(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return render(request, "core/no_role.html")
    route = {
        "farmer": "farmer_dashboard",
        "mill": "mill_dashboard",
        "financier": "financier_dashboard",
        "regulator": "regulator_dashboard",
    }.get(profile.role)
    return redirect(route) if route else render(request, "core/no_role.html")

@role_required("farmer")
def farmer_dashboard(request):
    farmer = get_object_or_404(Farmer, user=request.user)
    receivables = (
        Receivable.objects.filter(delivery__farmer=farmer)
        .select_related("delivery", "delivery__mill")
        .order_by("-created_at")
    )
    metrics = {
        "amount_outstanding": receivables.exclude(status__in=["settled","cancelled"]).aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "available_now": receivables.filter(status="verified").aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "financed": receivables.filter(status="financed").aggregate(v=Sum("amount"))["v"] or Decimal("0"),
    }
    return render(request, "core/farmer_dashboard.html", {"farmer": farmer, "receivables": receivables, "metrics": metrics})

@role_required("mill")
def mill_dashboard(request):
    mills = mill_queryset_for_user(request.user)
    deliveries = Delivery.objects.filter(mill__in=mills).select_related("farmer__user","farm","mill").order_by("-delivered_at")[:100]
    receivables = Receivable.objects.filter(delivery__mill__in=mills).select_related("delivery","delivery__farmer__user","delivery__mill").order_by("-created_at")[:100]
    metrics = {
        "outstanding": receivables.exclude(status__in=["settled","cancelled"]).aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "finance_linked": receivables.filter(status="financed").aggregate(v=Sum("amount"))["v"] or Decimal("0"),
        "pending_verification": deliveries.filter(status="pending").count(),
    }
    return render(request, "core/mill_dashboard.html", {"deliveries": deliveries, "receivables": receivables, "metrics": metrics})

@role_required("mill")
def delivery_create(request):
    if request.method == "POST":
        form = DeliveryForm(request.POST, user=request.user)
        if form.is_valid():
            delivery = form.save(commit=False)
            delivery.reference = f"MWD-{timezone.localdate():%y%m%d}-{uuid.uuid4().hex[:6].upper()}"
            delivery.source_system = "manual"
            delivery.save()
            audit(request.user, "delivery_created", delivery, f"Manual delivery {delivery.reference} created.")
            messages.success(request, "Delivery captured. Verify it when the source record is confirmed.")
            return redirect("mill_dashboard")
    else:
        form = DeliveryForm(user=request.user, initial={"delivered_at": timezone.localtime().strftime("%Y-%m-%dT%H:%M")})
    return render(request, "core/form.html", {
        "form": form,
        "title": "Register cane delivery",
        "eyebrow": "MILL OPERATIONS",
        "description": "Capture the source delivery record. Verification creates the basis for a mill payment obligation.",
        "button": "Save delivery",
    })

@role_required("mill")
@transaction.atomic
def verify_delivery(request, pk):
    delivery = get_object_or_404(
        Delivery.objects.select_for_update(),
        pk=pk, mill__in=mill_queryset_for_user(request.user)
    )
    if request.method == "POST" and delivery.status == "pending":
        delivery.status = "verified"
        delivery.mill_approved = True
        delivery.verified_by = request.user
        delivery.verified_at = timezone.now()
        delivery.save(update_fields=["status","mill_approved","verified_by","verified_at"])

        due_date = delivery.delivered_at.date() + timedelta(days=delivery.mill.payment_terms_days)
        receivable, _ = Receivable.objects.get_or_create(
            delivery=delivery,
            defaults={
                "reference": f"MWR-{delivery.id:07d}",
                "amount": delivery.amount_payable,
                "due_date": due_date,
                "status": "draft",
            },
        )
        receivable.amount = delivery.amount_payable
        receivable.due_date = due_date
        receivable.save(update_fields=["amount","due_date"])
        audit(request.user, "delivery_verified", delivery, f"Delivery verified; net mill obligation KES {delivery.amount_payable:,.2f}.")
        messages.success(request, "Delivery verified. The receivable is now waiting for mill acknowledgement.")
    return redirect("mill_dashboard")

@role_required("mill")
@transaction.atomic
def acknowledge_receivable(request, pk):
    receivable = get_object_or_404(
        Receivable.objects.select_for_update().select_related("delivery"),
        pk=pk, delivery__mill__in=mill_queryset_for_user(request.user)
    )
    if request.method == "POST" and not receivable.mill_acknowledged:
        receivable.mill_acknowledged = True
        receivable.acknowledged_by = request.user
        receivable.acknowledged_at = timezone.now()
        receivable.status = "verified"
        receivable.save()
        receivable.delivery.status = "acknowledged"
        receivable.delivery.save(update_fields=["status"])
        audit(request.user, "mill_obligation_acknowledged", receivable, f"Mill acknowledged KES {receivable.amount:,.2f} payable.")
        messages.success(request, "Obligation acknowledged. The farmer can now wait for mill payment or request early financing.")
    return redirect("mill_dashboard")

@role_required("farmer")
@transaction.atomic
def request_finance(request, pk):
    farmer = get_object_or_404(Farmer, user=request.user)
    receivable = get_object_or_404(
        Receivable.objects.select_for_update(),
        pk=pk, delivery__farmer=farmer, mill_acknowledged=True, status="verified"
    )
    if hasattr(receivable, "assignment"):
        messages.error(request, "This receivable has already been financed.")
        return redirect("receivable_detail", pk=receivable.pk)
    if hasattr(receivable, "finance_request"):
        messages.info(request, "A financing request already exists for this receivable.")
        return redirect("receivable_detail", pk=receivable.pk)

    if request.method == "POST":
        form = FinanceRequestForm(request.POST)
        if form.is_valid():
            requested = form.cleaned_data["requested_amount"]
            if requested > receivable.amount:
                form.add_error("requested_amount", "The request cannot exceed the amount the mill owes.")
            else:
                fr = FinanceRequest.objects.create(
                    receivable=receivable, farmer=farmer, requested_amount=requested,
                    consent_to_share=form.cleaned_data["consent_to_share"]
                )
                receivable.status = "finance_requested"
                receivable.save(update_fields=["status"])
                audit(request.user, "finance_requested", fr, f"Farmer authorised financing review for KES {requested:,.2f}.")
                messages.success(request, "Request shared with participating banks and SACCOs.")
                return redirect("receivable_detail", pk=receivable.pk)
    else:
        form = FinanceRequestForm(initial={"requested_amount": receivable.amount})

    return render(request, "core/form.html", {
        "form": form,
        "title": "Get paid sooner",
        "eyebrow": "EARLY PAYMENT",
        "description": f"The mill has acknowledged {receivable.reference}. Choose how much of the verified KES {receivable.amount:,.2f} obligation you want financiers to review.",
        "button": "Request offers",
    })

@role_required("farmer")
def receivable_detail(request, pk):
    farmer = get_object_or_404(Farmer, user=request.user)
    receivable = get_object_or_404(
        Receivable.objects.select_related("delivery","delivery__mill","delivery__farm"),
        pk=pk, delivery__farmer=farmer
    )
    offers = []
    if hasattr(receivable, "finance_request"):
        offers = receivable.finance_request.offers.select_related("financier","financier__profile").order_by("-advance_amount")
    return render(request, "core/receivable_detail.html", {"receivable": receivable, "offers": offers})

@role_required("financier")
def financier_dashboard(request):
    requests = (
        FinanceRequest.objects.filter(
            status="open", consent_to_share=True,
            receivable__mill_acknowledged=True,
            receivable__assignment__isnull=True,
        )
        .select_related("farmer__user","receivable__delivery__mill","receivable__delivery")
        .order_by("-created_at")
    )
    my_offers = FinanceOffer.objects.filter(financier=request.user).select_related(
        "request__receivable","request__farmer__user"
    ).order_by("-created_at")
    accepted = my_offers.filter(status__in=["accepted","disbursed"])
    metrics = {
        "open_requests": requests.count(),
        "committed": accepted.aggregate(v=Sum("advance_amount"))["v"] or Decimal("0"),
        "awaiting_settlement": accepted.filter(request__receivable__status="financed").aggregate(v=Sum("settlement_amount"))["v"] or Decimal("0"),
    }
    return render(request, "core/financier_dashboard.html", {"requests": requests, "my_offers": my_offers, "metrics": metrics})

@role_required("financier")
def finance_request_detail(request, pk):
    fr = get_object_or_404(
        FinanceRequest.objects.select_related(
            "farmer__user","receivable__delivery__mill","receivable__delivery__farm","receivable__delivery"
        ),
        pk=pk, status="open", consent_to_share=True, receivable__assignment__isnull=True
    )
    return render(request, "core/finance_request_detail.html", {"fr": fr})

@role_required("financier")
def make_offer(request, pk):
    fr = get_object_or_404(
        FinanceRequest.objects.select_related("receivable"),
        pk=pk, status="open", consent_to_share=True, receivable__assignment__isnull=True
    )
    if request.method == "POST":
        form = FinanceOfferForm(request.POST)
        if form.is_valid():
            offer = form.save(commit=False)
            offer.request = fr
            offer.financier = request.user
            offer.settlement_amount = form.cleaned_data["advance_amount"] + form.cleaned_data["finance_cost"]
            if offer.advance_amount > fr.requested_amount:
                form.add_error("advance_amount", "Advance cannot exceed the farmer's request.")
            elif offer.settlement_amount > fr.receivable.amount:
                form.add_error(None, "Advance plus financing cost cannot exceed the verified mill obligation.")
            else:
                offer.save()
                audit(request.user, "finance_offer_created", offer, f"Offer: KES {offer.advance_amount:,.2f} advance; KES {offer.finance_cost:,.2f} cost.")
                messages.success(request, "Offer submitted to the farmer.")
                return redirect("financier_dashboard")
    else:
        suggested = (fr.requested_amount * Decimal("0.95")).quantize(Decimal("0.01"))
        form = FinanceOfferForm(initial={"advance_amount": suggested, "finance_cost": fr.receivable.amount - suggested})

    return render(request, "core/form.html", {
        "form": form,
        "title": f"Offer financing for {fr.receivable.reference}",
        "eyebrow": "BANK / SACCO OFFER",
        "description": f"The farmer requested KES {fr.requested_amount:,.2f}. The verified mill obligation is KES {fr.receivable.amount:,.2f}.",
        "button": "Submit offer",
    })

@role_required("farmer")
@transaction.atomic
def accept_offer(request, pk):
    if request.method != "POST":
        return redirect("farmer_dashboard")
    farmer = get_object_or_404(Farmer, user=request.user)
    offer = get_object_or_404(
        FinanceOffer.objects.select_for_update().select_related("request__receivable"),
        pk=pk, request__farmer=farmer, status="offered"
    )
    receivable = Receivable.objects.select_for_update().get(pk=offer.request.receivable_id)
    if ReceivableAssignment.objects.filter(receivable=receivable, active=True).exists():
        messages.error(request, "This receivable has already been financed.")
        return redirect("receivable_detail", pk=receivable.pk)

    FinanceOffer.objects.filter(request=offer.request, status="offered").exclude(pk=offer.pk).update(status="declined")
    offer.status = "accepted"
    offer.accepted_at = timezone.now()
    offer.save(update_fields=["status","accepted_at"])
    offer.request.status = "accepted"
    offer.request.save(update_fields=["status"])
    receivable.status = "financed"
    receivable.save(update_fields=["status"])
    ReceivableAssignment.objects.create(receivable=receivable, offer=offer, assigned_to=offer.financier)
    audit(request.user, "finance_offer_accepted", offer, f"Farmer accepted KES {offer.advance_amount:,.2f}; receivable locked.")
    messages.success(request, "Offer accepted. This receivable is now locked to the selected financier.")
    return redirect("receivable_detail", pk=receivable.pk)

@role_required("financier")
@transaction.atomic
def mark_disbursed(request, pk):
    offer = get_object_or_404(FinanceOffer.objects.select_for_update(), pk=pk, financier=request.user, status="accepted")
    if request.method == "POST":
        offer.status = "disbursed"
        offer.disbursed_at = timezone.now()
        offer.save(update_fields=["status","disbursed_at"])
        audit(request.user, "farmer_advance_disbursed", offer, f"Financier recorded KES {offer.advance_amount:,.2f} paid to farmer.")
        messages.success(request, "Farmer advance recorded as disbursed.")
    return redirect("financier_dashboard")

@role_required("mill")
@transaction.atomic
def settle_receivable(request, pk):
    receivable = get_object_or_404(
        Receivable.objects.select_for_update().select_related("delivery"),
        pk=pk, delivery__mill__in=mill_queryset_for_user(request.user)
    )
    if request.method != "POST" or receivable.status == "settled":
        return redirect("mill_dashboard")

    financier = None
    amount_to_financier = Decimal("0")
    amount_to_farmer = receivable.amount
    destination = "Farmer"

    if hasattr(receivable, "assignment") and receivable.assignment.active:
        offer = receivable.assignment.offer
        if offer.status != "disbursed":
            messages.error(request, "This receivable is assigned but the farmer advance is not marked as disbursed.")
            return redirect("mill_dashboard")
        financier = receivable.assignment.assigned_to
        amount_to_financier = offer.settlement_amount
        amount_to_farmer = max(Decimal("0"), receivable.amount - amount_to_financier)
        destination = getattr(getattr(financier, "profile", None), "organisation", "") or financier.username

    settlement = Settlement.objects.create(
        receivable=receivable,
        financier=financier,
        amount_received=receivable.amount,
        amount_to_financier=amount_to_financier,
        amount_to_farmer=amount_to_farmer,
        payment_destination=destination,
        reference=f"MWS-{receivable.id:07d}",
    )
    receivable.status = "settled"
    receivable.save(update_fields=["status"])
    receivable.delivery.status = "settled"
    receivable.delivery.save(update_fields=["status"])
    if hasattr(receivable, "finance_request"):
        receivable.finance_request.offers.filter(status="offered").update(status="declined")
        receivable.finance_request.status = "closed"
        receivable.finance_request.save(update_fields=["status"])
    if hasattr(receivable, "assignment"):
        receivable.assignment.active = False
        receivable.assignment.save(update_fields=["active"])

    audit(request.user, "mill_settlement_recorded", settlement, f"Settlement KES {receivable.amount:,.2f}; financier KES {amount_to_financier:,.2f}; farmer residual KES {amount_to_farmer:,.2f}.")
    messages.success(request, "Settlement recorded and the receivable closed.")
    return redirect("mill_dashboard")

@role_required("regulator")
def regulator_dashboard(request):
    totals = Receivable.objects.aggregate(total=Sum("amount"), count=Count("id"))
    outstanding = Receivable.objects.exclude(status__in=["settled","cancelled"]).aggregate(total=Sum("amount"), count=Count("id"))
    financed = Receivable.objects.filter(status="financed").aggregate(total=Sum("amount"), count=Count("id"))
    settled = Receivable.objects.filter(status="settled").aggregate(total=Sum("amount"), count=Count("id"))
    mills = Mill.objects.all().order_by("name")
    events = AuditEvent.objects.select_related("actor").all()[:100]
    connectors = IntegrationConnection.objects.all().order_by("name")
    return render(request, "core/regulator_dashboard.html", {
        "totals": totals, "outstanding": outstanding, "financed": financed,
        "settled": settled, "mills": mills, "events": events, "connectors": connectors
    })

@role_required("regulator")
def integration_hub(request):
    return render(request, "core/integration_hub.html", {
        "connections": IntegrationConnection.objects.all().order_by("name"),
        "events": IntegrationEvent.objects.select_related("connection").all()[:100],
        "ingest_enabled": bool(settings.MIWA360_INGEST_KEY),
    })

@login_required
def api_receivable(request, reference):
    r = get_object_or_404(Receivable.objects.select_related("delivery__mill","delivery__farmer__user"), reference=reference)
    role = getattr(getattr(request.user, "profile", None), "role", None)
    can_view = role in {"mill","financier","regulator"} or (role == "farmer" and r.delivery.farmer.user_id == request.user.id)
    if not can_view:
        return JsonResponse({"detail":"forbidden"}, status=403)
    assignment = getattr(r, "assignment", None)
    return JsonResponse({
        "reference": r.reference,
        "verified": r.mill_acknowledged,
        "amount": str(r.amount),
        "farmer_number": r.delivery.farmer.farmer_number,
        "mill": r.delivery.mill.name,
        "delivery_reference": r.delivery.reference,
        "delivery_ticket": r.delivery.delivery_ticket_number,
        "source_system": r.delivery.source_system,
        "status": r.status,
        "finance_locked": bool(assignment and assignment.active),
        "due_date": r.due_date.isoformat(),
    })

def _integration_event(connection, status, external_reference, detail):
    IntegrationEvent.objects.create(
        connection=connection, direction="inbound", event_type="delivery_ingest",
        external_reference=external_reference or "", status=status, detail=detail
    )

@csrf_exempt
@require_POST
def ingest_delivery(request):
    expected = settings.MIWA360_INGEST_KEY
    supplied = request.headers.get("X-MIWA360-KEY", "")
    connection = IntegrationConnection.objects.filter(code="delivery-api").first()

    if not expected or not supplied or not secrets.compare_digest(expected, supplied):
        _integration_event(connection, "rejected", "", "Invalid or missing integration key.")
        return JsonResponse({"detail":"unauthorised"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        _integration_event(connection, "rejected", "", "Invalid JSON payload.")
        return JsonResponse({"detail":"invalid_json"}, status=400)

    required = ["source_system","external_reference","farmer_number","farm_code","mill_code","delivered_at","gross_weight_tonnes","accepted_weight_tonnes","price_per_tonne"]
    missing = [key for key in required if payload.get(key) in (None,"")]
    if missing:
        _integration_event(connection, "rejected", payload.get("external_reference",""), f"Missing fields: {', '.join(missing)}")
        return JsonResponse({"detail":"missing_fields","fields":missing}, status=400)

    source_system = payload["source_system"]
    valid_sources = {choice[0] for choice in Delivery.SOURCE_CHOICES}
    if source_system not in valid_sources or source_system == "manual":
        return JsonResponse({"detail":"invalid_source_system"}, status=400)

    try:
        farmer = Farmer.objects.get(farmer_number=payload["farmer_number"], verified=True)
        farm = Farm.objects.get(farm_code=payload["farm_code"], farmer=farmer)
        mill = Mill.objects.get(code=payload["mill_code"], verified=True)
    except (Farmer.DoesNotExist, Farm.DoesNotExist, Mill.DoesNotExist):
        _integration_event(connection, "rejected", payload["external_reference"], "Farmer, farm or mill is unknown / unverified.")
        return JsonResponse({"detail":"unknown_counterparty"}, status=422)

    dt = parse_datetime(payload["delivered_at"])
    if not dt:
        return JsonResponse({"detail":"invalid_delivered_at"}, status=400)

    try:
        gross_weight = Decimal(str(payload["gross_weight_tonnes"]))
        accepted_weight = Decimal(str(payload["accepted_weight_tonnes"]))
        price = Decimal(str(payload["price_per_tonne"]))
        deductions = Decimal(str(payload.get("deductions","0")))
        quality = payload.get("quality_score")
        quality = Decimal(str(quality)) if quality not in (None,"") else None
    except (InvalidOperation, TypeError):
        return JsonResponse({"detail":"invalid_numeric_value"}, status=400)

    external_reference = str(payload["external_reference"]).strip()

    with transaction.atomic():
        existing = Delivery.objects.select_for_update().filter(
            source_system=source_system, external_reference=external_reference
        ).first()

        if existing and hasattr(existing, "receivable"):
            existing_receivable = existing.receivable
            assignment = getattr(existing_receivable, "assignment", None)
            if existing_receivable.status in {"financed", "settled"} or (assignment and assignment.active):
                _integration_event(
                    connection, "rejected", external_reference,
                    "Attempted update to a finance-locked or settled receivable."
                )
                return JsonResponse({"detail": "record_locked"}, status=409)

        created = existing is None
        delivery = existing or Delivery(
            reference=f"MWD-{timezone.localdate():%y%m%d}-{uuid.uuid4().hex[:6].upper()}",
            source_system=source_system, external_reference=external_reference
        )
        delivery.farmer = farmer
        delivery.farm = farm
        delivery.mill = mill
        delivery.delivery_ticket_number = str(payload.get("delivery_ticket_number",""))
        delivery.delivered_at = dt
        delivery.gross_weight_tonnes = gross_weight
        delivery.accepted_weight_tonnes = accepted_weight
        delivery.quality_score = quality
        delivery.price_per_tonne = price
        delivery.deductions = deductions
        delivery.imported_at = timezone.now()
        mill_approved = bool(payload.get("mill_approved", False))
        obligation_acknowledged = bool(payload.get("obligation_acknowledged", False))
        delivery.mill_approved = mill_approved
        delivery.status = "verified" if mill_approved else "pending"
        if mill_approved and not delivery.verified_at:
            delivery.verified_at = timezone.now()
        delivery.save()

        receivable = None
        if mill_approved:
            due_date = delivery.delivered_at.date() + timedelta(days=mill.payment_terms_days)
            receivable, _ = Receivable.objects.get_or_create(
                delivery=delivery,
                defaults={
                    "reference": f"MWR-{delivery.id:07d}",
                    "amount": delivery.amount_payable,
                    "due_date": due_date,
                    "status": "draft",
                }
            )
            receivable.amount = delivery.amount_payable
            receivable.due_date = due_date
            if obligation_acknowledged:
                receivable.mill_acknowledged = True
                receivable.acknowledged_at = receivable.acknowledged_at or timezone.now()
                receivable.status = "verified"
                delivery.status = "acknowledged"
                delivery.save(update_fields=["status"])
            receivable.save()

        _integration_event(connection, "success", external_reference, f"{'Created' if created else 'Updated'} delivery {delivery.reference}.")

    return JsonResponse({
        "delivery_reference": delivery.reference,
        "created": created,
        "status": delivery.status,
        "receivable_reference": receivable.reference if receivable else None,
        "receivable_status": receivable.status if receivable else None,
    }, status=201 if created else 200)
