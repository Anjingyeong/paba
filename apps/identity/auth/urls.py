from __future__ import annotations

from django.urls import path

from . import views

app_name = "auth"

urlpatterns = [
    path("login/", views.manager_login, name="login"),
    path("mfa/setup/", views.manager_mfa_setup, name="mfa_setup"),
    path("mfa/", views.manager_mfa, name="mfa"),
    path("logout/", views.manager_logout, name="logout"),
    path("reauth/", views.manager_reauth, name="reauth"),
]
