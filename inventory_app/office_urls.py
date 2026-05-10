"""
Office Portal URL Configuration
All routes prefixed with /office/ (configured in config/urls.py)
"""
from django.urls import path
from . import office_views

urlpatterns = [
    path('dashboard/',           office_views.office_dashboard,  name='office_dashboard'),
    path('jobs/',                office_views.office_job_list,   name='office_job_list'),
    path('jobs/create/',         office_views.office_job_create,  name='office_job_create'),
    path('jobs/<int:job_id>/edit/', office_views.office_job_edit, name='office_job_edit'),
    path('jobs/<int:job_id>/certificate/', office_views.generate_certificate_pdf, name='generate_certificate_pdf'),
    path('workers/',             office_views.office_worker_list, name='office_worker_list'),
    path('workers/create/',      office_views.office_worker_create, name='office_worker_create'),
    path('inventory/',           office_views.office_inventory,  name='office_inventory'),
    path('inventory/item/create/', office_views.office_item_create, name='office_item_create'),
    path('inventory/item/<int:item_id>/edit/', office_views.office_item_edit, name='office_item_edit'),
    path('inventory/location/create/', office_views.office_location_create, name='office_location_create'),
    path('inventory/location/<int:loc_id>/edit/', office_views.office_location_edit, name='office_location_edit'),
    path('inventory/stock/', office_views.office_stock_list, name='office_stock_list'),
    path('inventory/stock/create/', office_views.office_stock_create, name='office_stock_create'),
    path('inventory/stock/<int:stock_id>/edit/', office_views.office_stock_edit, name='office_stock_edit'),
    path('inventory/stock/add/', office_views.office_add_stock, name='office_add_stock'),
    path('inventory/usage/', office_views.office_usage_history, name='office_usage_history'),

    # JSON APIs (Quick Edit)
    path('api/cha/<int:pk>/', office_views.api_cha_detail, name='api_cha_detail'),
    path('api/cha/save/', office_views.api_cha_save, name='api_cha_save'),
    path('api/exporter/<int:pk>/', office_views.api_exporter_detail, name='api_exporter_detail'),
    path('api/exporter/save/', office_views.api_exporter_save, name='api_exporter_save'),
    path('api/client/create/', office_views.api_create_client, name='api_create_client'),
    path('api/job/<int:pk>/', office_views.api_get_job_data, name='api_job_data'),
]
