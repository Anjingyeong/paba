from __future__ import annotations

from django.urls import path

from . import manager_views

app_name = "identity_manager"

urlpatterns = [
    path("manager/employees/create/", manager_views.create_employee, name="create_employee"),
    path(
        "manager/employees/<str:employee_code>/reset-pin/",
        manager_views.reset_employee_pin,
        name="reset_employee_pin",
    ),
    path(
        "manager/employees/<str:employee_code>/terminate/",
        manager_views.terminate_employee,
        name="terminate_employee",
    ),
]