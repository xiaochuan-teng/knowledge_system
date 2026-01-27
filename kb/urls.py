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
]
