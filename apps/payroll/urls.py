from __future__ import annotations

from django.urls import path

from . import views

app_name = "payroll"

urlpatterns = [
    path("manager/payroll/wage/", views.update_hourly_wage, name="update_hourly_wage"),
    path(
        "manager/payroll/settings/",
        views.update_payroll_settings,
        name="update_payroll_settings",
    ),
    path("manager/payroll/close/", views.close_month, name="close_month"),
    path("manager/payroll/reopen/", views.reopen_month, name="reopen_month"),
    path("manager/payroll/statements/", views.download_statements, name="download_statements"),
]
