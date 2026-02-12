"""
URL configuration for knowledge_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # 认证相关
    path('login/', auth_views.LoginView.as_view(template_name='kb/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='article_list'), name='logout'),

    # 知识文章
    path('', views.article_list, name='article_list'),
    path('article/<int:pk>/', views.article_detail, name='article_detail'),
    path('article/new/', views.article_create, name='article_create'),
    path('article/<int:pk>/edit/', views.article_edit, name='article_edit'),
    path('article/<int:pk>/delete/', views.article_delete, name='article_delete'),

    # 其他页面
    path('about/', views.about, name='about'),
    path('profile/', views.profile, name='profile'),

    # 虚拟机管理
    path('vms/', views.vm_list, name='vm_list'),
    path('vm/new/', views.vm_create, name='vm_create'),
    path('vm/<int:pk>/', views.vm_detail, name='vm_detail'),
    path('vm/<int:pk>/edit/', views.vm_edit, name='vm_edit'),
    path('vm/<int:pk>/delete/', views.vm_delete, name='vm_delete'),
    path('vm/update-status-now/', views.vm_update_status_now, name='vm_update_status_now'),
    path('host/<int:host_id>/vm-status-summary/', views.host_vm_status_summary, name='host_vm_status_summary'),

    # 虚拟机电源操作
    path('vm/<int:pk>/power-status/', views.get_vm_power_status, name='vm_power_status'),
    path('vm/<int:pk>/power-operation/', views.vm_power_operation, name='vm_power_operation'),
	
    # 仪表板
    path('dashboard/', views.dashboard, name='dashboard'),

    # 用户管理URL
    path('users/', views.user_list, name='user_list'),
    path('user/new/', views.user_create, name='user_create'),
    path('user/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('user/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # 数据导出URL
    path('export/articles/', views.export_articles_csv, name='export_articles'),
    path('export/vms/', views.export_vms_csv, name='export_vms'),

    # kb/urls.py
    path('settings/', views.system_settings, name='system_settings'),

    # 资产管理
    path('assets/', views.asset_list, name='asset_list'),
    path('assets/dashboard/', views.asset_dashboard, name='asset_dashboard'),
    path('asset/<int:pk>/', views.asset_detail, name='asset_detail'),
    path('asset/new/', views.asset_create, name='asset_create'),
    path('asset/<int:pk>/edit/', views.asset_edit, name='asset_edit'),
    path('asset/<int:pk>/delete/', views.asset_delete, name='asset_delete'),
    path('assets/export/', views.export_assets_csv, name='export_assets'),
    path('assets/quick-check/', views.asset_quick_check, name='asset_quick_check'),

    # 自动发布模块
    path('deployment/', views.deployment_dashboard, name='deployment_dashboard'),
    
    # 项目管理
    path('deployment/projects/', views.project_list, name='project_list'),
    path('deployment/project/new/', views.project_create, name='project_create'),
    path('deployment/project/<int:pk>/', views.project_detail, name='project_detail'),
    path('deployment/project/<int:pk>/edit/', views.project_edit, name='project_edit'),
    path('deployment/project/<int:pk>/delete/', views.project_delete, name='project_delete'),
    path('deployment/project/<int:pk>/script/', views.script_edit, name='script_edit'),
    
    # 包管理
    path('deployment/packages/', views.package_list, name='package_list'),
    path('deployment/package/upload/', views.package_upload, name='package_upload'),
    
    # 任务管理
    path('deployment/tasks/', views.task_list, name='task_list'),
    path('deployment/task/<int:pk>/', views.task_detail, name='task_detail'),
    path('deployment/task/<int:pk>/progress/', views.task_progress, name='task_progress'),
    
    # 历史记录
    path('deployment/history/', views.history_list, name='history_list'),
    path('deployment/history/<int:pk>/', views.history_detail, name='history_detail'),
    
    # API接口
    path('api/virtual-machines/search/', views.vm_search_api, name='vm_search_api'),
    path('api/project/<int:pk>/vm-status/', views.project_vm_status_api, name='project_vm_status_api'),
    path('api/virtual-machines/<int:pk>/info/', views.vm_detail_api, name='vm_detail_api'),
    path('api/task/<int:pk>/detail/', views.task_detail_api, name='task_detail_api'),
    path('api/tasks/status/', views.tasks_status_api, name='tasks_status_api'),
    path('api/tasks/delete/', views.tasks_delete_api, name='tasks_delete_api'),
    path('api/task/<int:pk>/start/', views.task_start_api, name='task_start_api'),
    path('api/task/<int:pk>/cancel/', views.task_cancel_api, name='task_cancel_api'),
    path('api/task/<int:pk>/retry/', views.task_retry_api, name='task_retry_api'),
    path('api/project/<int:pk>/default-script/', views.project_default_script_api, name='project_default_script_api'),
    path('api/project/<int:pk>/validate-script/', views.project_validate_script_api, name='project_validate_script_api'),
    path('api/project/<int:pk>/test-script/', views.project_test_script_api, name='project_test_script_api'),
    path('api/project/<int:pk>/toggle-script/', views.project_toggle_script_api, name='project_toggle_script_api'),
    path('api/task/<int:pk>/status/', views.task_status_api, name='task_status_api'),
    path('api/projects/search/', views.project_search_api, name='project_search_api'),
    path('api/project/<int:pk>/health-check/', views.project_vm_health_check_api, name='project_vm_health_check_api'),
]
