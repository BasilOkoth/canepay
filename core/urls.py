from django.urls import path
from . import views
from .auth_views import account_pending, signup

urlpatterns = [
    path("", views.home, name="home"),
    path("accounts/create/", signup, name="signup"),
    path("accounts/pending/", account_pending, name="account_pending"),
    path("farmer/", views.farmer_dashboard, name="farmer_dashboard"),
    path("farmer/receivable/<int:pk>/", views.receivable_detail, name="receivable_detail"),
    path("farmer/receivable/<int:pk>/finance/", views.request_finance, name="request_finance"),
    path("farmer/offer/<int:pk>/accept/", views.accept_offer, name="accept_offer"),
    path("mill/", views.mill_dashboard, name="mill_dashboard"),
    path("mill/delivery/new/", views.delivery_create, name="delivery_create"),
    path("mill/delivery/<int:pk>/verify/", views.verify_delivery, name="verify_delivery"),
    path("mill/receivable/<int:pk>/acknowledge/", views.acknowledge_receivable, name="acknowledge_receivable"),
    path("mill/receivable/<int:pk>/settle/", views.settle_receivable, name="settle_receivable"),
    path("financier/", views.financier_dashboard, name="financier_dashboard"),
    path("financier/request/<int:pk>/", views.finance_request_detail, name="finance_request_detail"),
    path("financier/request/<int:pk>/offer/", views.make_offer, name="make_offer"),
    path("financier/offer/<int:pk>/disbursed/", views.mark_disbursed, name="mark_disbursed"),
    path("oversight/", views.regulator_dashboard, name="regulator_dashboard"),
    path("oversight/integrations/", views.integration_hub, name="integration_hub"),
    path("api/v1/receivables/<str:reference>/", views.api_receivable, name="api_receivable"),
    path("api/v1/integrations/deliveries/", views.ingest_delivery, name="ingest_delivery"),
]
