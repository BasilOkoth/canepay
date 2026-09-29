from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .decorators import role_required
from .forms import FarmExpenseForm
from .models import Delivery, Farm, Farmer, FarmExpense, Receivable, Settlement


ZERO = Decimal("0")


@role_required("farmer")
def farmer_dashboard(request):
    farmer = get_object_or_404(Farmer, user=request.user)

    deliveries = (
        Delivery.objects.filter(farmer=farmer)
        .select_related("farm", "mill")
        .order_by("-delivered_at")
    )
    receivables = (
        Receivable.objects.filter(delivery__farmer=farmer)
        .select_related("delivery", "delivery__mill", "delivery__farm")
        .order_by("-created_at")
    )
    settlements = (
        Settlement.objects.filter(receivable__delivery__farmer=farmer)
        .select_related("receivable", "receivable__delivery", "receivable__delivery__mill", "financier")
        .order_by("-settled_at")
    )
    expenses = (
        FarmExpense.objects.filter(farmer=farmer)
        .select_related("farm")
        .order_by("-expense_date")
    )

    total_tonnes = deliveries.aggregate(v=Sum("accepted_weight_tonnes"))["v"] or ZERO
    total_revenue = sum((d.amount_payable for d in deliveries), ZERO)
    total_expenses = expenses.aggregate(v=Sum("amount"))["v"] or ZERO
    net_profit = total_revenue - total_expenses
    profit_margin = (net_profit / total_revenue * Decimal("100")) if total_revenue > 0 else ZERO
    total_acres = farmer.farms.aggregate(v=Sum("acreage"))["v"] or ZERO
    profit_per_acre = (net_profit / total_acres) if total_acres > 0 else ZERO
    profit_per_tonne = (net_profit / total_tonnes) if total_tonnes > 0 else ZERO

    metrics = {
        "amount_outstanding": receivables.exclude(status__in=["settled", "cancelled"]).aggregate(v=Sum("amount"))["v"] or ZERO,
        "available_now": receivables.filter(status="verified").aggregate(v=Sum("amount"))["v"] or ZERO,
        "financed": receivables.filter(status="financed").aggregate(v=Sum("amount"))["v"] or ZERO,
        "paid_to_farmer": settlements.aggregate(v=Sum("amount_to_farmer"))["v"] or ZERO,
        "total_tonnes": total_tonnes,
        "total_revenue": total_revenue,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "profit_margin": profit_margin,
        "profit_per_acre": profit_per_acre,
        "profit_per_tonne": profit_per_tonne,
    }

    farm_rows = []
    for farm in farmer.farms.all().order_by("farm_code"):
        farm_deliveries = deliveries.filter(farm=farm)
        farm_tonnes = farm_deliveries.aggregate(v=Sum("accepted_weight_tonnes"))["v"] or ZERO
        farm_revenue = sum((d.amount_payable for d in farm_deliveries), ZERO)
        farm_cost = expenses.filter(farm=farm).aggregate(v=Sum("amount"))["v"] or ZERO
        farm_profit = farm_revenue - farm_cost
        farm_rows.append({
            "farm": farm,
            "tonnes": farm_tonnes,
            "revenue": farm_revenue,
            "cost": farm_cost,
            "profit": farm_profit,
            "profit_per_acre": (farm_profit / farm.acreage) if farm.acreage else ZERO,
        })

    return render(request, "core/farmer_dashboard.html", {
        "farmer": farmer,
        "metrics": metrics,
        "deliveries": deliveries[:20],
        "receivables": receivables[:20],
        "settlements": settlements[:20],
        "expenses": expenses[:10],
        "farm_rows": farm_rows,
        "today": timezone.localdate(),
    })


@role_required("farmer")
def expense_create(request):
    farmer = get_object_or_404(Farmer, user=request.user)
    if request.method == "POST":
        form = FarmExpenseForm(request.POST, farmer=farmer)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.farmer = farmer
            expense.save()
            messages.success(request, "Farm cost added. Profitability figures have been updated.")
            return redirect("farmer_dashboard")
    else:
        form = FarmExpenseForm(farmer=farmer)

    return render(request, "core/form.html", {
        "form": form,
        "title": "Add farm cost",
        "eyebrow": "FARM PROFITABILITY",
        "description": "Record a production or operating cost so CanePay can calculate real farm profitability.",
        "button": "Save cost",
    })
