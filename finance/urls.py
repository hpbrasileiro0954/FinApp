from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('params/', views.params_list, name='params'),
    path('params/create/', views.params_create, name='params_create'),
    path('params/<int:pk>/edit/', views.params_edit, name='params_edit'),
    path('params/<int:pk>/delete/', views.params_delete, name='params_delete'),

    path('categories/', views.categories_list, name='categories'),
    path('categories/create/', views.categories_create, name='categories_create'),
    path('categories/<int:pk>/edit/', views.categories_edit, name='categories_edit'),
    path('categories/<int:pk>/delete/', views.categories_delete, name='categories_delete'),

    path('entries/', views.entries_list, name='entries'),
    path('entries/create/', views.entries_create, name='entries_create'),
    path('entries/<int:pk>/edit/', views.entries_edit, name='entries_edit'),
    path('entries/<int:pk>/delete/', views.entries_delete, name='entries_delete'),
    path('entries/category-hint/', views.entries_category_hint, name='entries_category_hint'),
    path('entries/database/edit/', views.entries_database_edit, name='entries_database_edit'),

    path('times/', views.times_view, name='times'),
    path('times/category-hint/', views.times_category_hint, name='times_category_hint'),
    path('times/generate/', views.times_generate, name='times_generate'),
    path('times/save/', views.times_save, name='times_save'),
    path('support/', views.support_view, name='support'),
    path('support/action/', views.support_action, name='support_action'),
    path('cards/', views.cards_view, name='cards'),
    path('fluxo/', views.fluxo_view, name='fluxo'),
    path('fluxo/detail/', views.fluxo_detail, name='fluxo_detail'),
    path('acumulado/', views.acumulado_view, name='acumulado'),
    path('sincronismo/', views.sincronismo_view, name='sincronismo'),
    path('sincronismo/sync/', views.sincronismo_sync, name='sincronismo_sync'),
    path('historico/', views.historico_view, name='historico'),
    path('historico/export/', views.historico_export, name='historico_export'),
    path('historico/<int:pk>/detail/', views.historico_detail, name='historico_detail'),
    path('historico/<int:pk>/delete/', views.historico_log_delete, name='historico_log_delete'),
]
