from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('', views.login_choice_view, name='login_choice'),
    path('login/', views.worker_login_view, name='worker_login'),
    path('admin-login/', views.admin_login_view, name='admin_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login_choice'), name='logout'),
    path('signup/', views.signup_view, name='signup'),
    
    # App Views
    path('jobs/', views.job_list_view, name='job_list'),
    path('job/<int:job_id>/', views.job_detail_view, name='job_detail'),
    path('job/<int:job_id>/complete/', views.mark_job_completed, name='job_complete'),
    path('job/<int:job_id>/certificate/', views.generate_certificate_pdf, name='generate_certificate_pdf'),
    path('job/<int:job_id>/json/', views.job_json_data, name='job_json_data'),
    path('history/', views.worker_history_view, name='worker_history'),
    path('inventory/report/', views.inventory_report_view, name='inventory_report'),
]
