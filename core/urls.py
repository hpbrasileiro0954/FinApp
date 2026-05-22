from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('approve/<int:user_id>/', views.approve_user_view, name='approve_user'),
    path('chart/', views.dashboard_chart_view, name='dashboard_chart'),
]
