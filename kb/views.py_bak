from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import HttpResponseForbidden, JsonResponse
from django.core.paginator import Paginator
from datetime import datetime, timedelta
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
import csv
from django.http import HttpResponse, JsonResponse
from django.utils.encoding import smart_str
from .models import CustomUser, Article, Attachment, Comment, HostMachine, VirtualMachine
from .forms import ArticleForm, CommentForm, VmForm
from .models import Asset, AssetCredential, AssetPhoto
from .forms import AssetForm, AssetCredentialFormSet, AssetPhotoFormSet
from datetime import date
import threading
import logging
from .tasks import update_vm_status_job
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views.decorators.http import require_GET
import paramiko
import os
import time
import threading
from django.db import transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import hashlib
import codecs  # 用于CSV导出
#from .models import Project, DeploymentServer, DeploymentPackage, DeploymentTask, DeploymentScript, TaskPackageRelation, TaskServerRelation
#from .forms_deployment import ProjectForm, DeploymentServerForm, DeploymentPackageForm, DeploymentTaskForm, DeploymentScriptForm, PackageUploadForm
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from django.urls import reverse

# 添加 logger 定义
logger = logging.getLogger(__name__)

def require_deployment_models(func):
    """装饰器确保部署相关模型在函数执行前可用"""
    def wrapper(request, *args, **kwargs):
        # 导入所有部署相关模型
        from .models import (
            Project, DeploymentServer, DeploymentPackage, 
            DeploymentTask, DeploymentScript, DeploymentHistory,
            TaskPackageRelation, TaskServerRelation, ProjectVMRelation
        )
        from .forms_deployment import (
            ProjectForm, DeploymentServerForm, DeploymentPackageForm,
            DeploymentTaskForm, DeploymentScriptForm, PackageUploadForm,
            ProjectVMFormSet  # 修改这一行：使用正确的表单集名称
        )
        
        # 将这些模型添加到函数的全局变量中
        import sys
        module = sys.modules[func.__module__]
        module.Project = Project
        module.DeploymentServer = DeploymentServer
        module.DeploymentPackage = DeploymentPackage
        module.DeploymentTask = DeploymentTask
        module.DeploymentScript = DeploymentScript
        module.DeploymentHistory = DeploymentHistory
        module.TaskPackageRelation = TaskPackageRelation
        module.TaskServerRelation = TaskServerRelation
        module.ProjectVMRelation = ProjectVMRelation
        module.ProjectForm = ProjectForm
        module.DeploymentServerForm = DeploymentServerForm
        module.DeploymentPackageForm = DeploymentPackageForm
        module.DeploymentTaskForm = DeploymentTaskForm
        module.DeploymentScriptForm = DeploymentScriptForm
        module.PackageUploadForm = PackageUploadForm
        module.ProjectVMFormSet = ProjectVMFormSet  # 修改这一行
        
        return func(request, *args, **kwargs)
    return wrapper


def get_deployment_models():
    """安全获取部署相关模型"""
    from .models import (
        Project, DeploymentServer, DeploymentPackage, DeploymentTask,
        DeploymentScript, DeploymentHistory, TaskPackageRelation,
        TaskServerRelation, ProjectVMRelation
    )
    return {
        'Project': Project,
        'DeploymentServer': DeploymentServer,
        'DeploymentPackage': DeploymentPackage,
        'DeploymentTask': DeploymentTask,
        'DeploymentScript': DeploymentScript,
        'DeploymentHistory': DeploymentHistory,
        'TaskPackageRelation': TaskPackageRelation,
        'TaskServerRelation': TaskServerRelation,
        'ProjectVMRelation': ProjectVMRelation,
    }

def get_deployment_forms():
    """安全获取部署相关表单"""
    from .forms_deployment import (
        ProjectForm, DeploymentServerForm, DeploymentPackageForm,
        DeploymentTaskForm, DeploymentScriptForm, PackageUploadForm
    )
    return {
        'ProjectForm': ProjectForm,
        'DeploymentServerForm': DeploymentServerForm,
        'DeploymentPackageForm': DeploymentPackageForm,
        'DeploymentTaskForm': DeploymentTaskForm,
        'DeploymentScriptForm': DeploymentScriptForm,
        'PackageUploadForm': PackageUploadForm,
    }


# ============ 辅助函数 ============
def get_article_type_display_name(article_type):
    """将文章类型代码转换为中文显示名"""
    type_map = {
        'product': '产品问题',
        'project': '项目问题',
        'network': '网络管理',
        'device': '设备使用',
        'package': '安装包制作',
        'test': '测试问题',
        'other': '其他',
    }
    return type_map.get(article_type, '其他')


# ============ 文章列表和详情 ============
def article_list(request):
    articles = Article.objects.all().order_by('-created_at')

    # 搜索功能
    search_query = request.GET.get('q', '')
    article_type = request.GET.get('type', '')
    resolved = request.GET.get('resolved', '')
    author_id = request.GET.get('author', '')

    # 构建查询条件
    filters = Q()

    if search_query:
        filters &= (
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(tags__icontains=search_query) |
                Q(product_version__icontains=search_query) |
                Q(project_name__icontains=search_query) |
                Q(author__username__icontains=search_query)
        )

    if article_type:
        filters &= Q(article_type=article_type)

    if resolved == 'yes':
        filters &= Q(is_resolved=True)
    elif resolved == 'no':
        filters &= Q(is_resolved=False)

    if author_id:
        filters &= Q(author_id=author_id)

    if filters:
        articles = articles.filter(filters)

    # 获取活跃作者列表（用于筛选）
    active_authors = CustomUser.objects.filter(
        article__isnull=False
    ).distinct().order_by('username')

    # 分页
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'article_type': article_type,
        'resolved': resolved,
        'author_id': author_id,
        'active_authors': active_authors,
        'type_name': get_article_type_display_name(article_type),
    }
    return render(request, 'kb/article_list.html', context)


def article_detail(request, pk):
    """文章详情页，包含评论功能"""
    article = get_object_or_404(Article, pk=pk)

    # 增加浏览次数
    article.views += 1
    article.save()

    # 处理评论提交
    if request.method == 'POST' and request.user.is_authenticated:
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.article = article
            comment.author = request.user
            comment.save()
            messages.success(request, '评论发布成功！')
            return redirect('article_detail', pk=pk)
    else:
        form = CommentForm()

    # 获取文章的所有标签（转换为列表）
    tag_list = article.tag_list()

    context = {
        'article': article,
        'tag_list': tag_list,
        'comments': article.comments.all(),
        'attachments': article.attachments.all(),
        'form': form,
    }
    return render(request, 'kb/article_detail.html', context)


# ============ 文章创建和编辑 ============
@login_required
def article_create(request):
    """创建新文章"""
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            article = form.save(commit=False)
            article.author = request.user
            article.save()

            # 处理附件上传
            files = request.FILES.getlist('attachments')
            for file in files:
                Attachment.objects.create(
                    article=article,
                    file=file,
                    file_name=file.name,
                    file_type=file.content_type
                )

            messages.success(request, '文章创建成功！')
            return redirect('article_detail', pk=article.pk)
        else:
            messages.error(request, '请检查表单中的错误')
    else:
        form = ArticleForm()

    return render(request, 'kb/article_form.html', {
        'form': form,
        'title': '创建新文章',
        'submit_text': '创建文章'
    })


@login_required
def article_edit(request, pk):
    """编辑文章（只能作者或管理员编辑）"""
    article = get_object_or_404(Article, pk=pk)

    # 权限检查：只能是作者或管理员
    if article.author != request.user and request.user.role != 'admin':
        return HttpResponseForbidden("您没有权限编辑此文章")

    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES, instance=article)
        if form.is_valid():
            article = form.save()

            # 处理新附件上传
            files = request.FILES.getlist('attachments')
            for file in files:
                Attachment.objects.create(
                    article=article,
                    file=file,
                    file_name=file.name,
                    file_type=file.content_type
                )

            messages.success(request, '文章更新成功！')
            return redirect('article_detail', pk=article.pk)
        else:
            messages.error(request, '请检查表单中的错误')
    else:
        form = ArticleForm(instance=article)

    return render(request, 'kb/article_form.html', {
        'form': form,
        'article': article,
        'title': '编辑文章',
        'submit_text': '更新文章',
        'editing': True
    })


@login_required
def article_delete(request, pk):
    """删除文章（只能作者或管理员）"""
    article = get_object_or_404(Article, pk=pk)

    # 权限检查：只能是作者或管理员
    if article.author != request.user and request.user.role != 'admin':
        return HttpResponseForbidden("您没有权限删除此文章")

    if request.method == 'POST':
        article_title = article.title
        article.delete()
        messages.success(request, f'文章 "{article_title}" 已删除！')
        return redirect('article_list')

    return render(request, 'kb/article_confirm_delete.html', {'article': article})


# ============ 其他视图 ============
def about(request):
    """关于页面"""
    return render(request, 'kb/about.html')


@login_required
def profile(request):
    """个人资料页面"""
    # 获取用户发表的文章数量
    article_count = Article.objects.filter(author=request.user).count()

    return render(request, 'kb/profile.html', {
        'user': request.user,
        'article_count': article_count,
    })


# ============ 虚拟机管理 ============
@login_required
def vm_list(request):
    """虚拟机列表"""
    vms = VirtualMachine.objects.all().order_by('host_machine', 'name')
    host_machines = HostMachine.objects.all().prefetch_related('virtual_machines')

    # 搜索功能
    search_query = request.GET.get('q', '')
    if search_query:
        vms = vms.filter(
            Q(name__icontains=search_query) |
            Q(ip_address__icontains=search_query)
        )
    
    # 分页，每页10条
    paginator = Paginator(vms, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 检查是否为 AJAX 请求
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 只返回表格部分
        return render(request, 'kb/_vm_table_partial.html', {
            'host_machines': host_machines,
            'page_obj': page_obj,
            'search_query': search_query,
        })
    
    return render(request, 'kb/vm_list.html', {
        'host_machines': host_machines,
        'page_obj': page_obj,
        'search_query': search_query,
    })


# 创建虚拟机
@login_required
def vm_create(request):
    if request.method == 'POST':
        form = VmForm(request.POST)
        if form.is_valid():
            vm = form.save()
            messages.success(request, '虚拟机创建成功！')
            return redirect('vm_list')
    else:
        form = VmForm()

    return render(request, 'kb/vm_form.html', {'form': form})


# 虚拟机详情
@login_required
def vm_detail(request, pk):
    vm = get_object_or_404(VirtualMachine, pk=pk)
    return render(request, 'kb/vm_detail.html', {'vm': vm})


# 编辑虚拟机
@login_required
def vm_edit(request, pk):
    vm = get_object_or_404(VirtualMachine, pk=pk)

    if request.method == 'POST':
        form = VmForm(request.POST, instance=vm)
        if form.is_valid():
            form.save()
            messages.success(request, '虚拟机更新成功！')
            return redirect('vm_detail', pk=vm.pk)
    else:
        form = VmForm(instance=vm)

    return render(request, 'kb/vm_form.html', {'form': form, 'vm': vm})


# 删除虚拟机
@login_required
def vm_delete(request, pk):
    vm = get_object_or_404(VirtualMachine, pk=pk)

    if request.method == 'POST':
        vm_name = vm.name  # 保存名称用于消息提示
        vm.delete()  # 实际执行删除
        messages.success(request, f'虚拟机 "{vm_name}" 删除成功！')
        return redirect('vm_list')

    return render(request, 'kb/vm_confirm_delete.html', {'vm': vm})


#立即获取虚拟机状态
@login_required
def vm_update_status_now(request):
    """立即更新虚拟机状态"""
    if request.method == 'POST':
        try:
            # 直接执行更新任务
            update_vm_status_job()
            
            # 这里添加一个小的延迟，确保任务开始执行
            import time
            time.sleep(1)
            
            # 返回 JSON 响应而不是重定向
            return JsonResponse({
                'success': True, 
                'message': '虚拟机状态更新任务已启动！请稍后查看状态变化。'
            })
            
        except Exception as e:
            logger.error(f"手动更新虚拟机状态失败: {e}")
            return JsonResponse({
                'success': False, 
                'message': f'更新虚拟机状态失败: {str(e)}'
            })
    else:
        return JsonResponse({
            'success': False, 
            'message': '无效的请求方法'
        })


@login_required
def get_vm_power_status(request, pk):
    """获取单个虚拟机的电源状态"""
    try:
        vm = get_object_or_404(VirtualMachine, pk=pk)
        host = vm.host_machine
        
        # 这里需要调用 VMware API 获取实际状态
        # 由于 VMware 连接代码较复杂，我们先创建一个独立的函数
        status_info = get_vmware_vm_status(host, vm.name)
        
        if status_info['success']:
            # 更新数据库中的状态
            vm.status = status_info['status']
            vm.updated_at = timezone.now()
            
            # 如果从 VMware 获取到 IP 地址，也更新
            if status_info.get('ip_address'):
                vm.ip_address = status_info['ip_address']
            
            vm.save()
            
            return JsonResponse({
                'success': True,
                'vm_id': vm.pk,
                'name': vm.name,
                'status': vm.status,
                'status_display': vm.get_status_display(),
                'ip_address': vm.ip_address,
                'host_name': host.name,
                'host_ip': host.ip_address,
                'message': '状态获取成功'
            })
        else:
            # VMware 获取失败，设置为故障状态
            vm.status = 'fault'
            vm.updated_at = timezone.now()
            vm.save()
            
            return JsonResponse({
                'success': False,
                'vm_id': vm.pk,
                'name': vm.name,
                'status': 'fault',
                'status_display': '故障',
                'host_name': host.name,
                'host_ip': host.ip_address,
                'message': f'获取虚拟机状态异常: {status_info["error"]}'
            })
            
    except VirtualMachine.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '虚拟机不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"获取虚拟机状态失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'服务器错误: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt  # 因为是 AJAX 请求，暂时豁免 CSRF
def vm_power_operation(request, pk):
    """执行电源操作"""
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': '只接受 POST 请求'
        }, status=400)
    
    try:
        vm = get_object_or_404(VirtualMachine, pk=pk)
        action = request.POST.get('action')
        
        if action not in ['start', 'shutdown', 'reboot']:
            return JsonResponse({
                'success': False,
                'message': '不支持的操作类型'
            }, status=400)
        
        # 执行电源操作
        result = execute_vm_power_operation(vm, action)
        
        if result['success']:
            # 操作成功，等待3秒后更新状态
            return JsonResponse({
                'success': True,
                'message': result['message'],
                'operation': action,
                'vm_id': vm.pk,
                'name': vm.name
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result['message']
            }, status=500)
            
    except Exception as e:
        logger.error(f"电源操作失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'操作失败: {str(e)}'
        }, status=500)


# 取宿主机的虚拟机状态摘要
@require_GET
def host_vm_status_summary(request, host_id):
    """获取宿主机的虚拟机状态摘要"""
    try:
        host = HostMachine.objects.get(id=host_id)
        summary = host.get_vm_status_summary()
        
        return JsonResponse({
            'success': True,
            'summary': summary,
            'host_name': host.name,
            'host_ip': host.ip_address
        })
    except HostMachine.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '宿主机不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# VMware 操作相关的辅助函数
def get_vmware_vm_status(host, vm_name):
    """
    通过 VMware API 获取虚拟机状态
    返回字典：{'success': bool, 'status': str, 'ip_address': str, 'error': str}
    """
    import ssl
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
    
    try:
        # 连接到 ESXi/vCenter
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        port = int(host.port) if host.port else 443
        
        si = SmartConnect(
            host=host.ip_address,
            user=host.username,
            pwd=host.password,
            port=port,
            sslContext=context
        )
        
        # 查找虚拟机
        content = si.RetrieveContent()
        container_view = content.viewManager.CreateContainerView(
            container=content.rootFolder,
            type=[vim.VirtualMachine],
            recursive=True
        )
        
        vm_found = None
        for vm in container_view.view:
            if vm.name == vm_name:
                vm_found = vm
                break
        
        container_view.Destroy()
        
        if not vm_found:
            Disconnect(si)
            return {
                'success': False,
                'status': 'fault',
                'error': f'在宿主机 {host.name} 上未找到虚拟机 {vm_name}'
            }
        
        # 获取状态
        power_state = vm_found.runtime.powerState
        ip_address = vm_found.guest.ipAddress if vm_found.guest else None
        
        # 映射 VMware 状态到本地状态
        status_mapping = {
            'poweredOn': 'running',
            'poweredOff': 'stopped',
            'suspended': 'stopped',
        }
        
        local_status = status_mapping.get(str(power_state), 'fault')
        
        # 更新宿主机最后检查时间
        host.last_check_time = timezone.now()
        host.save()
        
        Disconnect(si)
        
        return {
            'success': True,
            'status': local_status,
            'ip_address': ip_address,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"VMware API 调用失败: {e}")
        return {
            'success': False,
            'status': 'fault',
            'error': f'连接宿主机失败: {str(e)}'
        }


def execute_vm_power_operation(vm, action):
    """
    执行虚拟机电源操作
    返回字典：{'success': bool, 'message': str}
    """
    import ssl
    from pyVim.connect import SmartConnect, Disconnect
    from pyVmomi import vim
    import time
    
    try:
        host = vm.host_machine
        
        # 连接到 ESXi/vCenter
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        port = int(host.port) if host.port else 443
        
        si = SmartConnect(
            host=host.ip_address,
            user=host.username,
            pwd=host.password,
            port=port,
            sslContext=context
        )
        
        # 查找虚拟机
        content = si.RetrieveContent()
        container_view = content.viewManager.CreateContainerView(
            container=content.rootFolder,
            type=[vim.VirtualMachine],
            recursive=True
        )
        
        vmware_vm = None
        for v in container_view.view:
            if v.name == vm.name:
                vmware_vm = v
                break
        
        container_view.Destroy()
        
        if not vmware_vm:
            Disconnect(si)
            return {
                'success': False,
                'message': f'在宿主机上未找到虚拟机 {vm.name}'
            }
        
        result = {'success': False, 'message': ''}
        
        if action == 'start':
            # 开机操作
            if vmware_vm.runtime.powerState == 'poweredOn':
                result = {'success': True, 'message': '虚拟机已在运行状态'}
            else:
                task = vmware_vm.PowerOnVM_Task()
                task.wait()
                result = {'success': True, 'message': '开机命令已发送'}
        
        elif action == 'shutdown':
            # 关机操作：先尝试软关机，失败则硬关机
            if vmware_vm.runtime.powerState != 'poweredOn':
                result = {'success': True, 'message': '虚拟机已关机'}
            else:
                try:
                    # 先尝试软关机
                    vmware_vm.ShutdownGuest()
                    
                    # 等待5秒检查是否关机成功
                    time.sleep(5)
                    
                    # 重新获取虚拟机状态
                    content = si.RetrieveContent()
                    container_view = content.viewManager.CreateContainerView(
                        container=content.rootFolder,
                        type=[vim.VirtualMachine],
                        recursive=True
                    )
                    
                    for v in container_view.view:
                        if v.name == vm.name:
                            vmware_vm = v
                            break
                    
                    container_view.Destroy()
                    
                    if vmware_vm.runtime.powerState == 'poweredOff':
                        result = {'success': True, 'message': '软关机成功'}
                    else:
                        # 软关机失败，转为硬关机
                        task = vmware_vm.PowerOffVM_Task()
                        task.wait()
                        result = {'success': True, 'message': '硬关机成功'}
                        
                except Exception as e:
                    # 软关机失败，转为硬关机
                    try:
                        task = vmware_vm.PowerOffVM_Task()
                        task.wait()
                        result = {'success': True, 'message': '硬关机成功'}
                    except Exception as e2:
                        result = {'success': False, 'message': f'关机失败: {e2}'}
        
        elif action == 'reboot':
            # 重启操作：先尝试软重启，失败则硬重启
            if vmware_vm.runtime.powerState != 'poweredOn':
                result = {'success': False, 'message': '虚拟机已关机，无法重启'}
            else:
                try:
                    # 先尝试软重启
                    vmware_vm.RebootGuest()
                    result = {'success': True, 'message': '软重启命令已发送'}
                except Exception as e:
                    # 软重启失败，尝试硬重启（关机+开机）
                    try:
                        # 先关机
                        task_off = vmware_vm.PowerOffVM_Task()
                        task_off.wait()
                        
                        # 等待2秒
                        time.sleep(2)
                        
                        # 再开机
                        task_on = vmware_vm.PowerOnVM_Task()
                        task_on.wait()
                        
                        result = {'success': True, 'message': '硬重启成功'}
                    except Exception as e2:
                        result = {'success': False, 'message': f'重启失败: {e2}'}
        
        # 更新宿主机最后检查时间
        host.last_check_time = timezone.now()
        host.save()
        
        Disconnect(si)
        return result
        
    except Exception as e:
        logger.error(f"执行电源操作失败: {e}")
        return {
            'success': False,
            'message': f'执行操作失败: {str(e)}'
        }


# 仪表板首页
@login_required
def dashboard(request):
    # 基本统计
    total_articles = Article.objects.count()
    total_vms = VirtualMachine.objects.count()
    total_hosts = HostMachine.objects.count()
    total_users = CustomUser.objects.count()

    # 近7天新增文章
    week_ago = datetime.now() - timedelta(days=7)
    recent_articles = Article.objects.filter(created_at__gte=week_ago).count()

    # 文章按类型统计
    article_stats = Article.objects.values('article_type').annotate(
        count=Count('id')
    ).order_by('-count')

    # 虚拟机按状态统计
    vm_stats = VirtualMachine.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')

    # 虚拟机按操作系统统计
    os_stats = VirtualMachine.objects.values('os').annotate(
        count=Count('id')
    ).order_by('-count')

    # 最新文章
    latest_articles = Article.objects.all().order_by('-created_at')[:5]

    # 最新虚拟机
    latest_vms = VirtualMachine.objects.all().order_by('-created_at')[:5]
    
    # 为每个文章类型统计项添加中文显示名
    article_stats_with_display = []
    for stat in article_stats:
        stat_dict = dict(stat)  # 转换为字典
        stat_dict['display_name'] = get_article_type_display_name(stat['article_type'])
        article_stats_with_display.append(stat_dict)

    context = {
        'total_articles': total_articles,
        'total_vms': total_vms,
        'total_hosts': total_hosts,
        'total_users': total_users,
        'recent_articles': recent_articles,
        'article_stats': article_stats,
        'vm_stats': vm_stats,
	'os_stats': os_stats,
        'latest_articles': latest_articles,
        'latest_vms': latest_vms,
	'article_stats': article_stats_with_display,
    }

    return render(request, 'kb/dashboard.html', context)


# 检查用户是否有管理员权限的装饰器
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.role == 'admin':
            return view_func(request, *args, **kwargs)
        messages.error(request, '需要管理员权限！')
        return redirect('dashboard')

    return wrapper


# 用户列表（仅管理员）
@login_required
@admin_required
def user_list(request):
    users = CustomUser.objects.all().order_by('-date_joined')
    return render(request, 'kb/user_list.html', {'users': users})


# 创建用户（仅管理员）
@login_required
@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # 设置默认部门
            user.department = '交付部'
            user.save()
            messages.success(request, f'用户 {user.username} 创建成功！')
            return redirect('user_list')
    else:
        form = UserCreationForm()

    return render(request, 'kb/user_form.html', {'form': form})


# 编辑用户（仅管理员）
@login_required
@admin_required
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)

    if request.method == 'POST':
        # 简化处理，实际应该用表单
        user.role = request.POST.get('role', user.role)
        user.department = request.POST.get('department', user.department)
        user.save()
        messages.success(request, f'用户 {user.username} 更新成功！')
        return redirect('user_list')

    return render(request, 'kb/user_edit.html', {'user': user})


# 删除用户（仅管理员）
@login_required
@admin_required
def user_delete(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)

    if request.user == user:
        messages.error(request, '不能删除自己的账户！')
        return redirect('user_list')

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'用户 {username} 删除成功！')
        return redirect('user_list')

    return render(request, 'kb/user_confirm_delete.html', {'user': user})


# 导出文章数据
@login_required
def export_articles_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="articles.csv"'

    writer = csv.writer(response, csv.excel)
    response.write(codecs.BOM_UTF8)  # 支持中文

    # 写入标题行
    writer.writerow([
        smart_str('ID'),
        smart_str('标题'),
        smart_str('问题类型'),
        smart_str('产品版本'),
        smart_str('项目名称'),
        smart_str('作者'),
        smart_str('是否解决'),
        smart_str('浏览次数'),
        smart_str('创建时间'),
        smart_str('标签'),
    ])

    # 写入数据行
    articles = Article.objects.all().order_by('-created_at')
    for article in articles:
        writer.writerow([
            smart_str(article.id),
            smart_str(article.title),
            smart_str(article.get_article_type_display()),
            smart_str(article.product_version or ''),
            smart_str(article.project_name or ''),
            smart_str(article.author.username),
            smart_str('是' if article.is_resolved else '否'),
            smart_str(article.views),
            smart_str(article.created_at.strftime('%Y-%m-%d %H:%M')),
            smart_str(article.tags or ''),
        ])

    return response


# 导出虚拟机数据
@login_required
def export_vms_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="virtual_machines.csv"'

    writer = csv.writer(response, csv.excel)
    response.write(codecs.BOM_UTF8)  # 支持中文

    # 写入标题行
    writer.writerow([
        smart_str('ID'),
        smart_str('虚拟机名称'),
        smart_str('IP地址'),
        smart_str('宿主机'),
        smart_str('责任人'),
        smart_str('CPU'),
        smart_str('内存'),
        smart_str('磁盘'),
        smart_str('操作系统'),
        smart_str('状态'),
        smart_str('创建时间'),
        smart_str('备注'),
    ])

    # 写入数据行
    vms = VirtualMachine.objects.all().order_by('host_machine', 'name')
    for vm in vms:
        writer.writerow([
            smart_str(vm.id),
            smart_str(vm.name),
            smart_str(vm.ip_address),
            smart_str(vm.host_machine.name),
            smart_str(vm.owner.username if vm.owner else ''),
            smart_str(vm.cpu),
            smart_str(vm.memory),
            smart_str(vm.disk),
            smart_str(vm.get_os_display()),
            smart_str(vm.get_status_display()),
            smart_str(vm.created_at.strftime('%Y-%m-%d %H:%M')),
            smart_str(vm.notes or ''),
        ])

    return response


# 系统设置（仅管理员）
@login_required
@admin_required
def system_settings(request):
    if request.method == 'POST':
        # 这里可以添加系统设置保存逻辑
        messages.success(request, '系统设置已保存！')
        return redirect('system_settings')

    return render(request, 'kb/settings.html')


# 系统信息
def system_info(request):
    import platform
    import django

    context = {
        'python_version': platform.python_version(),
        'django_version': django.get_version(),
        'os_info': platform.platform(),
        'server_time': datetime.now(),
    }

    return render(request, 'kb/system_info.html', context)


# kb/views.py
@login_required
def system_settings(request):
    return render(request, 'kb/settings.html')


# ============ 资产管理视图 ============

@login_required
def asset_list(request):
    """资产列表"""
    assets = Asset.objects.all().order_by('-created_at')

    # 搜索和筛选
    search_query = request.GET.get('q', '')
    asset_type = request.GET.get('type', '')
    status = request.GET.get('status', '')
    responsible = request.GET.get('responsible', '')
    department = request.GET.get('department', '')

    filters = Q()

    if search_query:
        filters &= (
                Q(name__icontains=search_query) |
                Q(serial_number__icontains=search_query) |
                Q(ip_address__icontains=search_query) |
                Q(brand__icontains=search_query) |
                Q(model__icontains=search_query) |
                Q(responsible_person__icontains=search_query) |
                Q(notes__icontains=search_query)
        )

    if asset_type:
        filters &= Q(asset_type=asset_type)

    if status:
        filters &= Q(status=status)

    if responsible:
        filters &= Q(responsible_person__icontains=responsible)

    if department:
        filters &= Q(department__icontains=department)

    if filters:
        assets = assets.filter(filters)

    # 统计信息 - 修正：确保有数据
    total_count = assets.count()

    # 使用 values_list 获取具体的数据
    type_stats = Asset.objects.values('asset_type').annotate(count=Count('id')).order_by('-count')
    status_stats = Asset.objects.values('status').annotate(count=Count('id')).order_by('-count')

    # 获取使用中的资产数量（安全的写法）
    in_use_count = Asset.objects.filter(status='in_use').count()

    # 获取最常见的资产类型（安全的写法）
    most_common_type = type_stats.first() if type_stats else None

    # 分页
    paginator = Paginator(assets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 转换资产类型统计为中文
    type_stats_chinese = []
    for stat in type_stats:
        chinese_name = dict(Asset.ASSET_TYPE_CHOICES).get(stat['asset_type'], stat['asset_type'])
        type_stats_chinese.append({
            'asset_type': stat['asset_type'],
            'chinese_name': chinese_name,
            'count': stat['count']
        })

    # 转换状态统计为中文
    status_stats_chinese = []
    for stat in status_stats:
        chinese_name = dict(Asset.STATUS_CHOICES).get(stat['status'], stat['status'])
        status_stats_chinese.append({
            'status': stat['status'],
            'chinese_name': chinese_name,
            'count': stat['count']
        })

    context = {
        'page_obj': page_obj,
        'total_count': total_count,
        'type_stats': list(type_stats),  # 转换为列表
        'status_stats': list(status_stats),  # 转换为列表
        'in_use_count': in_use_count,
        'most_common_type': most_common_type,
        'search_query': search_query,
        'asset_type': asset_type,
        'status': status,
        'responsible': responsible,
        'department': department,
        'asset_types': Asset.ASSET_TYPE_CHOICES,
        'status_choices': Asset.STATUS_CHOICES,
        'today': date.today(),
	'type_stats': type_stats_chinese,  # 改为新的中文列表
        'status_stats': status_stats_chinese,  # 改为新的中文列表
    }
    return render(request, 'kb/asset_list.html', context)


@login_required
def asset_detail(request, pk):
    """资产详情"""
    asset = get_object_or_404(Asset, pk=pk)
    credentials = asset.credentials.all()
    photos = asset.photos.all()

    context = {
        'asset': asset,
        'credentials': credentials,
        'photos': photos,
    }
    return render(request, 'kb/asset_detail.html', context)


@login_required
def asset_create(request):
    """创建资产"""
    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES)
        credential_formset = AssetCredentialFormSet(request.POST, prefix='credentials')
        photo_formset = AssetPhotoFormSet(request.POST, request.FILES, prefix='photos')

        if form.is_valid():
            asset = form.save(commit=False)
            asset.created_by = request.user
            asset.save()

            # 保存凭据表单集
            if credential_formset.is_valid():
                credential_formset.instance = asset
                credential_formset.save()

            # 保存照片表单集
            if photo_formset.is_valid():
                photo_formset.instance = asset
                photo_formset.save()

            messages.success(request, '资产创建成功！')
            return redirect('asset_detail', pk=asset.pk)
        else:
            messages.error(request, '请检查表单中的错误')
    else:
        form = AssetForm()
        credential_formset = AssetCredentialFormSet(prefix='credentials')
        photo_formset = AssetPhotoFormSet(prefix='photos')

    context = {
        'form': form,
        'credential_formset': credential_formset,
        'photo_formset': photo_formset,
        'title': '创建新资产',
        'submit_text': '创建资产',
    }
    return render(request, 'kb/asset_form.html', context)


@login_required
def asset_edit(request, pk):
    """编辑资产"""
    asset = get_object_or_404(Asset, pk=pk)

    if request.method == 'POST':
        form = AssetForm(request.POST, request.FILES, instance=asset)
        credential_formset = AssetCredentialFormSet(request.POST, instance=asset, prefix='credentials')
        photo_formset = AssetPhotoFormSet(request.POST, request.FILES, instance=asset, prefix='photos')

        if form.is_valid():
            asset = form.save()

            if credential_formset.is_valid():
                credential_formset.save()

            if photo_formset.is_valid():
                photo_formset.save()

            messages.success(request, '资产更新成功！')
            return redirect('asset_detail', pk=asset.pk)
        else:
            messages.error(request, '请检查表单中的错误')
    else:
        form = AssetForm(instance=asset)
        credential_formset = AssetCredentialFormSet(instance=asset, prefix='credentials')
        photo_formset = AssetPhotoFormSet(instance=asset, prefix='photos')

    context = {
        'form': form,
        'credential_formset': credential_formset,
        'photo_formset': photo_formset,
        'asset': asset,
        'title': '编辑资产信息',
        'submit_text': '更新资产',
        'editing': True,
    }
    return render(request, 'kb/asset_form.html', context)


@login_required
def asset_delete(request, pk):
    """删除资产"""
    asset = get_object_or_404(Asset, pk=pk)

    if request.method == 'POST':
        asset_name = asset.name
        asset.delete()
        messages.success(request, f'资产 "{asset_name}" 删除成功！')
        return redirect('asset_list')

    return render(request, 'kb/asset_confirm_delete.html', {'asset': asset})


@login_required
def asset_dashboard(request):
    """资产仪表板"""
    # 资产统计
    total_assets = Asset.objects.count()
    by_type = Asset.objects.values('asset_type').annotate(count=Count('id')).order_by('-count')
    by_status = Asset.objects.values('status').annotate(count=Count('id')).order_by('-count')
    by_department = Asset.objects.values('department').annotate(count=Count('id')).order_by('-count')

    # 即将过期的许可
    from datetime import date, timedelta
    thirty_days_later = date.today() + timedelta(days=30)
    expiring_licenses = Asset.objects.filter(
        license_expiry__isnull=False,
        license_expiry__gte=date.today(),
        license_expiry__lte=thirty_days_later
    ).order_by('license_expiry')

    # 最近更新的资产
    recent_assets = Asset.objects.all().order_by('-updated_at')[:10]

    context = {
        'total_assets': total_assets,
        'by_type': by_type,
        'by_status': by_status,
        'by_department': by_department,
        'expiring_licenses': expiring_licenses,
        'recent_assets': recent_assets,
    }
    return render(request, 'kb/asset_dashboard.html', context)


@login_required
def export_assets_csv(request):
    """导出资产数据到CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="assets.csv"'

    writer = csv.writer(response, csv.excel)
    response.write(codecs.BOM_UTF8)  # 支持中文

    # 写入标题行
    writer.writerow([
        smart_str('ID'),
        smart_str('资产名称'),
        smart_str('资产类型'),
        smart_str('品牌'),
        smart_str('型号'),
        smart_str('序列号'),
        smart_str('IP地址'),
        smart_str('负责人'),
        smart_str('部门'),
        smart_str('状态'),
        smart_str('许可到期'),
        smart_str('创建时间'),
    ])

    # 写入数据行
    assets = Asset.objects.all().order_by('-created_at')
    for asset in assets:
        writer.writerow([
            smart_str(asset.id),
            smart_str(asset.name),
            smart_str(asset.get_asset_type_display()),
            smart_str(asset.brand or ''),
            smart_str(asset.model or ''),
            smart_str(asset.serial_number or ''),
            smart_str(asset.ip_address or ''),
            smart_str(asset.responsible_person),
            smart_str(asset.department),
            smart_str(asset.get_status_display()),
            smart_str(asset.license_expiry.strftime('%Y-%m-%d') if asset.license_expiry else ''),
            smart_str(asset.created_at.strftime('%Y-%m-%d %H:%M')),
        ])

    return response


@login_required
def asset_quick_check(request):
    """快速资产检查（AJAX接口）"""
    if request.method == 'GET':
        query = request.GET.get('q', '')
        results = []

        if query:
            # 搜索资产
            assets = Asset.objects.filter(
                Q(name__icontains=query) |
                Q(serial_number__icontains=query) |
                Q(ip_address__icontains=query) |
                Q(responsible_person__icontains=query)
            )[:10]

            for asset in assets:
                results.append({
                    'id': asset.id,
                    'name': asset.name,
                    'type': asset.get_asset_type_display(),
                    'ip': asset.ip_address,
                    'responsible': asset.responsible_person,
                    'status': asset.get_status_display(),
                    'status_color': asset.get_status_color(),
                })

        return JsonResponse({'results': results})

    return JsonResponse({'error': 'Invalid request'}, status=400)

# ============ 部署项目管理 ============
@login_required
@require_deployment_models
def deployment_project_list(request):
    """部署项目列表"""
    projects = Project.objects.all().order_by('-created_at')
    
    # 搜索功能
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query) |
            Q(code__icontains=search_query) |
            Q(description__icontains=search_query)  # 修复这里
        )
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    # 分页
    paginator = Paginator(projects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'kb/deployment/project_list.html', context)


@login_required
@require_deployment_models
def deployment_project_create(request):
    """创建部署项目"""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            
            # 创建默认部署脚本
            default_script = get_default_deployment_script(project)
            DeploymentScript.objects.create(
                project=project,
                name='update.sh',
                content=default_script,
                created_by=request.user
            )
            
            messages.success(request, '项目创建成功！')
            return redirect('deployment_project_list')
    else:
        form = ProjectForm()
    
    return render(request, 'kb/deployment/project_form.html', {
        'form': form,
        'title': '创建新项目',
        'submit_text': '创建项目'
    })


@login_required
@require_deployment_models
def deployment_project_detail(request, pk):
    """项目详情"""
    project = get_object_or_404(Project, pk=pk)
    servers = project.servers.all()
    scripts = DeploymentScript.objects.filter(project=project)
    recent_tasks = DeploymentTask.objects.filter(project=project).order_by('-created_at')[:5]
    
    context = {
        'project': project,
        'servers': servers,
        'scripts': scripts,
        'recent_tasks': recent_tasks,
    }
    return render(request, 'kb/deployment/project_detail.html', context)


@login_required
@require_deployment_models
def deployment_server_test_connection(request, pk):
    """测试服务器连接"""
    server = get_object_or_404(DeploymentServer, pk=pk)
    
    try:
        # 测试SSH连接
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 如果有密钥则使用密钥，否则使用密码
        if server.ssh_key_path and os.path.exists(server.ssh_key_path):
            ssh.connect(server.ip_address, port=server.ssh_port,
                       username=server.ssh_username,
                       key_filename=server.ssh_key_path,
                       timeout=10)
        else:
            ssh.connect(server.ip_address, port=server.ssh_port,
                       username=server.ssh_username,
                       password=server.ssh_password,
                       timeout=10)
        
        # 测试基本命令
        stdin, stdout, stderr = ssh.exec_command('uname -a')
        os_info = stdout.read().decode().strip()
        
        # 检查C++和Java路径是否存在
        stdin, stdout, stderr = ssh.exec_command(f'ls -la {server.cpp_install_path}')
        cpp_exists = "No such file" not in stderr.read().decode()
        
        stdin, stdout, stderr = ssh.exec_command(f'ls -la {server.java_install_path}')
        java_exists = "No such file" not in stderr.read().decode()
        
        ssh.close()
        
        # 更新服务器状态
        server.is_online = True
        server.last_check_time = timezone.now()
        server.save()
        
        return JsonResponse({
            'success': True,
            'message': f'连接成功！操作系统信息: {os_info}',
            'cpp_exists': cpp_exists,
            'java_exists': java_exists,
        })
        
    except Exception as e:
        server.is_online = False
        server.last_check_time = timezone.now()
        server.save()
        
        return JsonResponse({
            'success': False,
            'message': f'连接失败: {str(e)}'
        })


@login_required
@csrf_exempt
@require_deployment_models
def deployment_task_start(request, pk):
    """开始执行部署任务"""
    task = get_object_or_404(DeploymentTask, pk=pk)
    
    if task.status not in ['pending', 'uploaded']:
        return JsonResponse({
            'success': False,
            'message': '任务状态不允许开始部署'
        })
    
    # 异步执行部署任务
    import threading
    thread = threading.Thread(target=execute_deployment_task, args=(task.pk,))
    thread.daemon = True
    thread.start()
    
    task.status = 'deploying'
    task.started_at = timezone.now()
    task.save()
    
    return JsonResponse({
        'success': True,
        'message': '部署任务已开始执行'
    })


@login_required
@require_deployment_models
def deployment_task_progress(request, pk):
    """获取任务进度"""
    task = get_object_or_404(DeploymentTask, pk=pk)
    
    # 获取服务器部署进度
    server_relations = TaskServerRelation.objects.filter(task=task)
    server_data = []
    total_progress = 0
    
    for relation in server_relations:
        server_data.append({
            'id': relation.server.id,
            'name': relation.server.name,
            'status': relation.deploy_status,
            'progress': relation.deploy_progress,
        })
        total_progress += relation.deploy_progress
    
    if server_relations.exists():
        task.progress = total_progress // server_relations.count()
        task.save()
    
    return JsonResponse({
        'task_status': task.status,
        'task_progress': task.progress,
        'servers': server_data,
        'log_content': task.log_content[-5000:] if task.log_content else '',  # 返回最后5000字符
    })


def execute_deployment_task(task_id):
    """执行部署任务（异步）- 完整版本"""
    from django.utils import timezone
    import traceback
    import socket
    import os
    import time
    
    try:
        # 获取任务对象
        task = DeploymentTask.objects.get(id=task_id)
        
        # 检查任务是否已被取消
        if task.status == 'cancelled':
            task.log_content = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务已被取消，停止执行\n"
            task.completed_at = timezone.now()
            task.save()
            return
        
        # 设置任务状态为上传中
        task.status = 'uploading'
        task.started_at = timezone.now()
        task.log_content = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行部署任务...\n项目: {task.project.name}\n包: {task.package.name}\n版本: {task.package.version}\n"
        task.save()
        
        # 获取项目、包和虚拟机关系
        project = task.project
        package = task.package
        vm_relations = project.projectvmrelation_set.select_related('virtual_machine')
        
        # 检查是否有虚拟机
        if not vm_relations.exists():
            task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 错误: 项目中没有配置虚拟机\n"
            task.status = 'failed'
            task.completed_at = timezone.now()
            task.save()
            return
        
        # 获取部署脚本
        try:
            script = project.deployment_script
            if not script.is_active:
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 警告: 部署脚本未启用，使用默认脚本\n"
                script_content = get_default_deployment_script(project)
            else:
                script_content = script.content
        except DeploymentScript.DoesNotExist:
            task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 使用默认部署脚本\n"
            script_content = get_default_deployment_script(project)
        
        total_vms = vm_relations.count()
        success_count = 0
        fail_count = 0
        skipped_count = 0
        
        # 开始逐个虚拟机部署
        task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始部署 {total_vms} 个虚拟机...\n"
        task.save()
        
        for i, vm_relation in enumerate(vm_relations):
            vm = vm_relation.virtual_machine
            target_ip = vm_relation.get_ip()
            
            # 检查任务是否已被取消
            task.refresh_from_db()
            if task.status == 'cancelled':
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务已被取消，停止执行\n"
                task.completed_at = timezone.now()
                task.save()
                return
            
            # 更新进度
            task.progress = int((i / total_vms) * 100)
            task.save()
            
            task.log_content += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] === 开始部署虚拟机: {vm.name} ({target_ip}) ===\n"
            task.save()
            
            try:
                # 检查虚拟机状态
                if vm.status != 'running':
                    task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 警告: 虚拟机 {vm.name} 状态为 {vm.get_status_display()}，跳过部署\n"
                    record_deployment_history(task, vm_relation, 'skipped', 
                                            f"虚拟机状态为 {vm.get_status_display()}，跳过部署")
                    skipped_count += 1
                    continue
                
                # 阶段1: 上传文件到目标服务器
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始上传文件...\n"
                task.save()
                
                upload_result = upload_file_to_server(vm_relation, package)
                
                if not upload_result['success']:
                    task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 文件上传失败: {upload_result['error']}\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'failed', 
                                            f"文件上传失败: {upload_result.get('error', '未知错误')}")
                    fail_count += 1
                    continue
                
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 文件上传成功，路径: {upload_result.get('remote_path', '未知')}\n"
                task.save()
                
                # 检查任务是否已被取消
                task.refresh_from_db()
                if task.status == 'cancelled':
                    task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务已被取消，停止执行\n"
                    task.completed_at = timezone.now()
                    task.save()
                    return
                
                # 阶段2: 执行部署脚本
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始执行部署脚本...\n"
                task.save()
                
                deploy_result = execute_deployment_script(vm_relation, script_content)
                
                if not deploy_result['success']:
                    task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 脚本执行失败: {deploy_result.get('error', '未知错误')}\n"
                    if deploy_result.get('output'):
                        task.log_content += f"输出: {deploy_result['output']}\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'failed',
                                            f"脚本执行失败: {deploy_result.get('error', '未知错误')}")
                    fail_count += 1
                    continue
                
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 脚本执行成功\n"
                if deploy_result.get('output'):
                    task.log_content += f"输出摘要: {deploy_result['output'][-500:] if len(deploy_result['output']) > 500 else deploy_result['output']}\n"
                task.save()
                
                # 检查任务是否已被取消
                task.refresh_from_db()
                if task.status == 'cancelled':
                    task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务已被取消，停止执行\n"
                    task.completed_at = timezone.now()
                    task.save()
                    return
                
                # 等待服务启动
                wait_time = project.health_check_timeout or 30
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 等待 {wait_time} 秒让服务启动...\n"
                task.save()
                time.sleep(wait_time)
                
                # 阶段3: 执行健康检查
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 开始健康检查...\n"
                task.save()
                
                health_result = perform_health_check(vm_relation, project)
                
                if health_result['success']:
                    task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 健康检查通过！\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'success',
                                            "部署成功，服务正常运行",
                                            java_healthy=health_result.get('java_healthy', False),
                                            cpp_healthy=health_result.get('cpp_healthy', False))
                    success_count += 1
                else:
                    task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 健康检查失败: {health_result['message']}\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'failed',
                                            f"健康检查失败: {health_result['message']}")
                    fail_count += 1
                    
            except Exception as e:
                error_msg = traceback.format_exc()
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 部署过程异常: {str(e)}\n详细错误: {error_msg[-1000:] if len(error_msg) > 1000 else error_msg}\n"
                task.save()
                record_deployment_history(task, vm_relation, 'failed', f"部署异常: {str(e)}")
                fail_count += 1
            
            # 更新进度
            task.progress = int(((i + 1) / total_vms) * 100)
            task.save()
        
        # 更新任务状态
        if fail_count == 0 and skipped_count == 0:
            task.status = 'success'
            task.log_content += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] === 所有虚拟机部署成功！ ===\n成功: {success_count}\n"
        elif success_count > 0 and fail_count > 0:
            task.status = 'partial'
            task.log_content += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] === 部署完成，部分成功 ===\n成功: {success_count}, 失败: {fail_count}, 跳过: {skipped_count}\n"
        elif success_count == 0 and fail_count > 0:
            task.status = 'failed'
            task.log_content += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] === 部署失败 ===\n成功: {success_count}, 失败: {fail_count}, 跳过: {skipped_count}\n"
        else:
            task.status = 'failed'
            task.log_content += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] === 部署异常 ===\n成功: {success_count}, 失败: {fail_count}, 跳过: {skipped_count}\n"
        
        task.completed_at = timezone.now()
        task.save()
        
        # 清理临时文件
        try:
            if os.path.exists(package.file_path):
                os.remove(package.file_path)
                task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 已清理临时文件: {package.file_path}\n"
                task.save()
        except Exception as e:
            task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 清理临时文件失败: {str(e)}\n"
            task.save()
        
    except DeploymentTask.DoesNotExist:
        logger.error(f"任务不存在: {task_id}")
    except Exception as e:
        error_msg = traceback.format_exc()
        try:
            task = DeploymentTask.objects.get(id=task_id)
            task.log_content += f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务执行异常: {str(e)}\n详细错误: {error_msg[-1000:] if len(error_msg) > 1000 else error_msg}\n"
            task.status = 'failed'
            task.completed_at = timezone.now()
            task.save()
        except:
            logger.error(f"任务异常且无法更新状态: {error_msg}")



def execute_remote_script(server, script_content):
    """在远程服务器上执行脚本"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接服务器
        if server.ssh_key_path and os.path.exists(server.ssh_key_path):
            ssh.connect(server.ip_address, port=server.ssh_port,
                       username=server.ssh_username,
                       key_filename=server.ssh_key_path,
                       timeout=30)
        else:
            ssh.connect(server.ip_address, port=server.ssh_port,
                       username=server.ssh_username,
                       password=server.ssh_password,
                       timeout=30)
        
        # 将脚本内容写入临时文件
        script_file = f"/tmp/deploy_{int(time.time())}.sh"
        sftp = ssh.open_sftp()
        
        # 创建脚本文件
        with sftp.file(script_file, 'w') as f:
            f.write(script_content)
        
        sftp.chmod(script_file, 0o755)
        sftp.close()
        
        # 执行脚本
        stdin, stdout, stderr = ssh.exec_command(f'bash {script_file}')
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        # 清理临时文件
        ssh.exec_command(f'rm -f {script_file}')
        ssh.close()
        
        return {
            'success': True if not error else False,
            'output': output,
            'error': error
        }
        
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e)
        }


def verify_deployment(server):
    """验证部署结果（完全基于端口判断）"""
    try:
        import socket
        import requests
        
        # 验证C++端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((server.ip_address, server.cpp_port))
        cpp_ok = result == 0
        sock.close()
        
        # 验证Java端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((server.ip_address, server.java_port))
        java_ok = result == 0
        sock.close()
        
        # 完全通过端口判断，不检查URL响应
        if cpp_ok and java_ok:
            return {
                'success': True,
                'message': '所有服务端口正常',
                'java_healthy': java_ok,
                'cpp_healthy': cpp_ok
            }
        else:
            error_details = []
            if not cpp_ok:
                error_details.append(f'C++端口 {server.cpp_port} 不可达')
            if not java_ok:
                error_details.append(f'Java端口 {server.java_port} 不可达')
            
            return {
                'success': False,
                'message': '; '.join(error_details),
                'java_healthy': java_ok,
                'cpp_healthy': cpp_ok
            }
            
    except Exception as e:
        return {
            'success': False,
            'message': f'健康检查过程中发生错误: {str(e)}',
            'java_healthy': False,
            'cpp_healthy': False
        }


# ============ 文件上传相关 ============
@login_required
@csrf_exempt
def deployment_upload_file(request, task_id):
    """上传文件到服务器"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只接受POST请求'})
    
    try:
        task = DeploymentTask.objects.get(id=task_id)
        package_id = request.POST.get('package_id')
        server_id = request.POST.get('server_id')
        
        package = DeploymentPackage.objects.get(id=package_id)
        server = DeploymentServer.objects.get(id=server_id)
        
        # 这里应该实现文件上传逻辑
        # 由于文件上传比较复杂，这里只提供框架
        
        return JsonResponse({
            'success': True,
            'message': '文件上传功能待实现'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# ============ 部署仪表板 ============
@login_required
def deployment_dashboard(request):
    """部署仪表板"""
    # 导入需要的模型
    from .models import Project, DeploymentPackage, DeploymentTask, VirtualMachine
    from django.utils import timezone
    
    today = timezone.now().date()
    
    # 统计信息
    active_projects_count = Project.objects.filter(status='active').count()
    total_projects = Project.objects.count()
    online_vms_count = VirtualMachine.objects.filter(status='running').count()
    total_vms = VirtualMachine.objects.count()
    today_tasks = DeploymentTask.objects.filter(created_at__date=today)
    today_tasks_count = today_tasks.count()
    
    # 计算今日任务成功率
    today_success_tasks = today_tasks.filter(status='success').count()
    success_rate = 0
    if today_tasks_count > 0:
        success_rate = round((today_success_tasks / today_tasks_count) * 100, 1)
    
    total_packages = DeploymentPackage.objects.count()
    active_packages = DeploymentPackage.objects.filter(is_active=True).count()
    
    # 最近任务（最近5个）
    recent_tasks = DeploymentTask.objects.all().order_by('-created_at')[:5]
    
    # 活跃项目列表（前5个活跃项目）
    active_projects_list = Project.objects.filter(status='active').prefetch_related('projectvmrelation_set')[:5]
    
    # 部署统计信息（用于侧边栏）
    deployment_stats_data = {
        'active_projects': active_projects_count,
        'online_vms': online_vms_count,
        'today_tasks': today_tasks_count,
        'success_rate': success_rate,
    }
    
    context = {
        'active_projects_count': active_projects_count,
        'total_projects': total_projects,
        'online_vms_count': online_vms_count,
        'total_vms': total_vms,
        'today_tasks_count': today_tasks_count,
        'success_rate': success_rate,
        'total_packages': total_packages,
        'active_packages': active_packages,
        'recent_tasks': recent_tasks,
        'active_projects': active_projects_list,
        'deployment_stats': deployment_stats_data,  # 添加部署统计信息
    }
    return render(request, 'kb/deployment/dashboard.html', context)


@login_required
@require_GET
@require_deployment_models
def deployment_project_servers_api(request, project_id):
    """获取项目下的服务器列表（API接口）"""
    try:
        project = Project.objects.get(id=project_id)
        servers = DeploymentServer.objects.filter(project=project)
        
        server_data = []
        for server in servers:
            server_data.append({
                'id': server.id,
                'name': server.name,
                'ip_address': server.ip_address,
                'is_online': server.is_online,
                'os_type': server.get_os_type_display(),
            })
        
        return JsonResponse({
            'success': True,
            'project_name': project.name,
            'servers': server_data,
        })
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)


def upload_file_to_server(vm_relation, package):
    """上传文件到服务器 - 直接使用原始文件名"""
    import paramiko
    from scp import SCPClient
    import os
    import time
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        target_ip = vm_relation.get_ip()
        ssh_port = vm_relation.ssh_port or 22
        ssh_username = vm_relation.ssh_username or 'root'
        ssh_password = vm_relation.ssh_password
        ssh_key_path = vm_relation.ssh_key_path
        
        # 连接超时时间
        timeout = 30
        
        # 连接服务器
        if ssh_key_path and os.path.exists(ssh_key_path):
            ssh.connect(target_ip, port=ssh_port,
                       username=ssh_username,
                       key_filename=ssh_key_path,
                       timeout=timeout)
        else:
            ssh.connect(target_ip, port=ssh_port,
                       username=ssh_username,
                       password=ssh_password,
                       timeout=timeout)
        
        # 创建目标目录
        ssh.exec_command('mkdir -p /opt')
        
        # 获取包文件的原始文件名
        original_filename = os.path.basename(package.file_path)
        
        # 在服务器上使用原始文件名
        remote_path = f"/opt/{original_filename}"
        
        print(f"上传文件到服务器: {original_filename} -> {target_ip}:{remote_path}")
        
        # 🔥 scp.put 是二进制传输，不会转换换行符，无需修改
        with SCPClient(ssh.get_transport()) as scp:
            scp.put(package.file_path, remote_path)
        
        # 设置执行权限（如果文件是可执行文件）
        if original_filename.endswith('.sh') or 'pcms' in original_filename:
            ssh.exec_command(f'chmod +x {remote_path}')
        
        # 验证文件是否上传成功
        stdin, stdout, stderr = ssh.exec_command(f'ls -la {remote_path}')
        result = stdout.read().decode().strip()
        print(f"验证文件上传结果: {result}")
        
        ssh.close()
        
        return {
            'success': True, 
            'remote_path': remote_path,
            'message': f'文件 {original_filename} 上传到 {remote_path} 成功'
        }
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"文件上传失败: {str(e)}")
        print(f"详细错误: {error_msg}")
        return {
            'success': False, 
            'error': str(e),
            'message': f'文件上传失败: {str(e)}'
        }


# ============ 项目管理 ============

@login_required
def project_list(request):
    """项目列表"""
    # 本地导入模型
    from .models import Project
    
    projects = Project.objects.all().order_by('-created_at')
    
    # 搜索功能
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        projects = projects.filter(
            Q(name__icontains=search_query) |  # 修复这里：移除多余的括号
            Q(code__icontains=search_query) |  # 修复这里：移除多余的括号
            Q(description__icontains=search_query)  # 修复这里：使用正确的语法
        )
    
    if status_filter:
        projects = projects.filter(status=status_filter)
    
    # 分页
    paginator = Paginator(projects, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
    }
    return render(request, 'kb/deployment/project_list.html', context)


@login_required
@require_deployment_models
def project_create(request):
    """创建项目"""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        vm_formset = ProjectVMFormSet(request.POST, prefix='vms')
        
        if form.is_valid() and vm_formset.is_valid():
            with transaction.atomic():
                project = form.save(commit=False)
                project.created_by = request.user
                project.save()
                
                # 由于 extra=0，我们需要检查是否有虚拟机数据
                vm_instances = vm_formset.save(commit=False)
                if vm_instances:
                    for vm_instance in vm_instances:
                        vm_instance.project = project
                        vm_instance.save()
                
                # 创建默认部署脚本
                default_script = get_default_deployment_script(project)
                DeploymentScript.objects.create(
                    project=project,
                    content=default_script
                )
            
            messages.success(request, '项目创建成功！')
            return redirect('project_detail', pk=project.pk)
        else:
            messages.error(request, '请检查表单中的错误')
    else:
        form = ProjectForm()
        # 初始化一个空表单集
        vm_formset = ProjectVMFormSet(prefix='vms', queryset=ProjectVMRelation.objects.none())
    
    return render(request, 'kb/deployment/project_form.html', {
        'form': form,
        'vm_formset': vm_formset,
        'title': '创建新项目',
        'submit_text': '创建项目'
    })


@login_required
@require_deployment_models
def project_detail(request, pk):
    """项目详情"""
    project = get_object_or_404(Project, pk=pk)
    vm_relations = project.projectvmrelation_set.select_related('virtual_machine')
    
    # 获取部署脚本
    try:
        script = project.deployment_script
    except DeploymentScript.DoesNotExist:
        script = None
    
    # 获取最近部署历史
    recent_history = DeploymentHistory.objects.filter(
        project_vm__project=project
    ).order_by('-completed_at')[:10]
    
    context = {
        'project': project,
        'vm_relations': vm_relations,
        'script': script,
        'recent_history': recent_history,
    }
    return render(request, 'kb/deployment/project_detail.html', context)


@login_required
@require_deployment_models
def project_edit(request, pk):
    """编辑项目"""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        vm_formset = ProjectVMFormSet(request.POST, instance=project, prefix='vms')  # 直接使用
        
        if form.is_valid() and vm_formset.is_valid():
            form.save()
            vm_formset.save()
            
            messages.success(request, '项目更新成功！')
            return redirect('project_detail', pk=project.pk)
        else:
            messages.error(request, '请检查表单中的错误')
    else:
        form = ProjectForm(instance=project)
        vm_formset = ProjectVMFormSet(instance=project, prefix='vms')  # 直接使用
    
    return render(request, 'kb/deployment/project_form.html', {
        'form': form,
        'vm_formset': vm_formset,
        'project': project,
        'title': '编辑项目',
        'submit_text': '更新项目',
        'editing': True
    })


@login_required
@require_deployment_models
def project_delete(request, pk):
    """删除项目"""
    project = get_object_or_404(Project, pk=pk)
    
    # 检查权限：只有管理员或项目创建者可以删除
    if not (request.user.role == 'admin' or project.created_by == request.user):
        messages.error(request, '您没有权限删除此项目！')
        return redirect('project_detail', pk=project.pk)
    
    if request.method == 'POST':
        try:
            project_name = project.name
            
            # 级联删除相关数据
            # 1. 删除项目关联的虚拟机关系
            project.projectvmrelation_set.all().delete()
            
            # 2. 删除部署脚本（如果存在）
            try:
                script = project.deployment_script
                script.delete()
            except DeploymentScript.DoesNotExist:
                pass
            
            # 3. 删除与该项目相关的部署任务和部署历史
            tasks = DeploymentTask.objects.filter(project=project)
            for task in tasks:
                # 删除任务相关的部署历史
                DeploymentHistory.objects.filter(task=task).delete()
                task.delete()
            
            # 4. 最后删除项目本身
            project.delete()
            
            messages.success(request, f'项目 "{project_name}" 删除成功！')
            return redirect('project_list')
            
        except Exception as e:
            messages.error(request, f'删除项目失败：{str(e)}')
            return redirect('project_detail', pk=project.pk)
    
    # GET 请求时显示确认页面
    return render(request, 'kb/deployment/project_confirm_delete.html', {
        'project': project,
        'vm_count': project.projectvmrelation_set.count(),
        'task_count': DeploymentTask.objects.filter(project=project).count(),
    })


@login_required
@require_deployment_models
def script_edit(request, pk):
    """编辑部署脚本"""
    project = get_object_or_404(Project, pk=pk)
    
    try:
        script = project.deployment_script
    except DeploymentScript.DoesNotExist:
        # 创建默认脚本（移除 created_by 参数）
        default_script = get_default_deployment_script(project)
        script = DeploymentScript.objects.create(
            project=project,
            content=default_script,
            # created_by=request.user  # 移除这行
        )
    
    if request.method == 'POST':
        form = DeploymentScriptForm(request.POST, instance=script)
        if form.is_valid():
            script = form.save(commit=False)
            # 增加版本号
            try:
                version = float(script.version) + 0.1
            except:
                version = 1.0
            script.version = str(version)
            script.save()
            
            messages.success(request, '部署脚本更新成功！')
            return redirect('project_detail', pk=project.pk)
    else:
        form = DeploymentScriptForm(instance=script)
    
    return render(request, 'kb/deployment/script_edit.html', {
        'form': form,
        'project': project,
        'title': '编辑部署脚本'
    })


# ============ 包上传与推送 ============

@login_required
def package_upload(request):
    """上传部署包并快速部署"""
    logger.info(f"package_upload 视图被调用，请求方法: {request.method}")
    
    if request.method == 'GET':
        # GET 请求：显示上传表单
        logger.info("处理 GET 请求，显示上传表单")
        try:
            # 尝试导入必要的模型和表单
            from .models import Project, DeploymentPackage, DeploymentTask
            from .forms_deployment import PackageUploadForm
            
            form = PackageUploadForm()
            return render(request, 'kb/deployment/package_upload.html', {
                'form': form,
                'title': '上传部署包并快速部署'
            })
        except Exception as e:
            logger.error(f"处理 GET 请求时出错: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'加载表单失败: {str(e)}'
            }, status=500)
    
    elif request.method == 'POST':
        # POST 请求：处理文件上传
        logger.info("处理 POST 请求，上传文件")
        
        # 首先确保导入必要的模块
        import os
        import uuid
        import hashlib
        import threading
        from django.utils.text import slugify
        from django.conf import settings
        
        try:
            # 导入模型和表单
            from .models import (
                Project, DeploymentPackage, DeploymentTask, 
                DeploymentScript, DeploymentHistory
            )
            from .forms_deployment import PackageUploadForm
            
            logger.info(f"请求内容类型: {request.content_type}")
            logger.info(f"请求大小: {request.headers.get('Content-Length', '未知')}")
            logger.info(f"FILES: {list(request.FILES.keys()) if request.FILES else '无文件'}")
            logger.info(f"POST 数据: {request.POST}")
            
            # 检查是否有文件
            if 'file' not in request.FILES:
                logger.error("请求中没有文件")
                return JsonResponse({
                    'success': False,
                    'message': '请选择要上传的文件'
                }, status=400)
            
            # 解析表单数据
            form = PackageUploadForm(request.POST, request.FILES)
            
            if not form.is_valid():
                logger.error(f"表单验证失败: {form.errors.as_json()}")
                return JsonResponse({
                    'success': False,
                    'message': '表单验证失败',
                    'errors': form.errors.as_json()
                }, status=400)
            
            # 表单验证成功，处理上传
            project = form.cleaned_data['project']
            package_type = form.cleaned_data['package_type']
            version = form.cleaned_data['version']
            description = form.cleaned_data['description']
            file = request.FILES['file']
            
            logger.info(f"文件信息 - 名称: {file.name}, 大小: {file.size}, 类型: {file.content_type}")
            
            # 检查项目是否有虚拟机
            from .models import ProjectVMRelation
            vm_count = ProjectVMRelation.objects.filter(project=project).count()
            logger.info(f"项目 {project.name} 有 {vm_count} 个虚拟机")
            
            if vm_count == 0:
                logger.warning(f"项目 {project.name} 没有关联任何虚拟机")
                return JsonResponse({
                    'success': False,
                    'message': '项目没有关联任何虚拟机，无法部署！'
                })
            
            # 创建上传目录
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'temp_packages')
            logger.info(f"上传目录路径: {upload_dir}")
            
            try:
                os.makedirs(upload_dir, exist_ok=True)
                logger.info(f"上传目录创建成功: {upload_dir}")
            except Exception as e:
                logger.error(f"创建上传目录失败: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'创建上传目录失败: {str(e)}'
                }, status=500)
            
            # 生成安全的文件名
            original_filename = file.name
            file_path = os.path.join(upload_dir, original_filename)
            # safe_filename = f"{slugify(original_filename.rsplit('.', 1)[0])}_{uuid.uuid4().hex[:8]}.{original_filename.rsplit('.', 1)[-1]}"
            # file_path = os.path.join(upload_dir, safe_filename)
            
            logger.info(f"保存文件路径: {file_path}")
            
            # 保存文件
            try:
                with open(file_path, 'wb+') as destination:
                    for chunk in file.chunks():
                        destination.write(chunk)
                file_size = os.path.getsize(file_path)
                logger.info(f"文件保存成功，实际大小: {file_size} 字节")
            except Exception as e:
                logger.error(f"保存文件失败: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': f'保存文件失败: {str(e)}'
                }, status=500)
            
            # 计算MD5
            try:
                md5_hash = hashlib.md5()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b''):
                        md5_hash.update(chunk)
                file_md5 = md5_hash.hexdigest()
                logger.info(f"文件MD5计算完成: {file_md5}")
            except Exception as e:
                logger.error(f"计算MD5失败: {str(e)}")
                # 删除已上传的文件
                try:
                    os.remove(file_path)
                except:
                    pass
                return JsonResponse({
                    'success': False,
                    'message': f'计算文件校验和失败: {str(e)}'
                }, status=500)
            
            # 创建包记录
            try:
                package = DeploymentPackage.objects.create(
                    name=original_filename,
                    package_type=package_type,
                    version=version,
                    file_path=file_path,
                    file_size=file.size,
                    md5_hash=file_md5,
                    description=description,
                    uploaded_by=request.user
                )
                logger.info(f"包记录创建成功，ID: {package.id}")
            except Exception as e:
                logger.error(f"创建包记录失败: {str(e)}", exc_info=True)
                # 清理文件
                try:
                    os.remove(file_path)
                except:
                    pass
                return JsonResponse({
                    'success': False,
                    'message': f'创建包记录失败: {str(e)}'
                }, status=500)
            
            # 创建部署任务
            try:
                from datetime import datetime
                task_name = f"快速部署-{project.name}-{version}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                task = DeploymentTask.objects.create(
                    project=project,
                    package=package,
                    name=task_name,
                    description=f"通过上传包触发的快速部署\n{description}",
                    created_by=request.user
                )
                logger.info(f"部署任务创建成功，ID: {task.id}")
            except Exception as e:
                logger.error(f"创建部署任务失败: {str(e)}", exc_info=True)
                # 删除包记录
                package.delete()
                # 清理文件
                try:
                    os.remove(file_path)
                except:
                    pass
                return JsonResponse({
                    'success': False,
                    'message': f'创建部署任务失败: {str(e)}'
                }, status=500)
            
            # 异步执行部署任务
            try:
                thread = threading.Thread(target=execute_deployment_task, args=(task.pk,))
                thread.daemon = True
                thread.start()
                logger.info(f"部署任务线程启动成功")
            except Exception as e:
                logger.error(f"启动部署任务线程失败: {str(e)}")
                # 这里不返回错误，因为任务记录已经创建，可以手动执行
            
            # 返回成功响应 - 使用 reverse 函数（确保已导入）
            response_data = {
                'success': True,
                'message': f'包 {original_filename} 上传成功！部署任务已开始执行。',
                'redirect_url': reverse('task_detail', kwargs={'pk': task.pk})
            }
            
            logger.info(f"文件上传处理完成，响应: {response_data}")
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"处理 POST 请求时发生异常: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'文件上传失败: {str(e)}'
            }, status=500)
    
    else:
        # 其他请求方法
        logger.warning(f"不支持的请求方法: {request.method}")
        return JsonResponse({
            'success': False,
            'message': f'不支持的请求方法: {request.method}'
        }, status=405)


def execute_deployment_task(task_id):
    """执行部署任务（异步）"""
    from django.utils import timezone
    
    try:
        task = DeploymentTask.objects.get(id=task_id)
        task.status = 'uploading'
        task.started_at = timezone.now()
        task.log_content = f"开始执行部署任务...\n项目: {task.project.name}\n包: {task.package.name}\n"
        task.save()
        
        project = task.project
        package = task.package
        vm_relations = project.projectvmrelation_set.select_related('virtual_machine')
        
        # 获取部署脚本
        try:
            script = project.deployment_script
            if not script.is_active:
                task.log_content += "警告：部署脚本未启用，使用默认脚本\n"
                script_content = get_default_deployment_script(project)
            else:
                script_content = script.content
        except DeploymentScript.DoesNotExist:
            task.log_content += "使用默认部署脚本\n"
            script_content = get_default_deployment_script(project)
        
        total_vms = vm_relations.count()
        success_count = 0
        fail_count = 0
        
        # 为每个虚拟机执行部署
        for i, vm_relation in enumerate(vm_relations):
            vm = vm_relation.virtual_machine
            target_ip = vm_relation.get_ip()
            
            task.log_content += f"\n=== 开始部署虚拟机: {vm.name} ({target_ip}) ===\n"
            task.save()
            
            try:
                # 上传文件到目标服务器
                upload_result = upload_file_to_server(vm_relation, package)
                
                if not upload_result['success']:
                    task.log_content += f"文件上传失败: {upload_result['error']}\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'failed', 
                                            f"文件上传失败: {upload_result['error']}")
                    fail_count += 1
                    continue
                
                task.log_content += f"文件上传成功，开始执行部署脚本...\n"
                task.save()
                
                # 执行部署脚本
                deploy_result = execute_deployment_script(vm_relation, script_content)
                
                if not deploy_result['success']:
                    task.log_content += f"脚本执行失败: {deploy_result['error']}\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'failed',
                                            f"脚本执行失败: {deploy_result['error']}")
                    fail_count += 1
                    continue
                
                task.log_content += f"脚本执行完成，开始健康检查...\n"
                task.save()
                
                # 执行健康检查
                health_result = perform_health_check(vm_relation, project)
                
                if health_result['success']:
                    task.log_content += f"健康检查通过！\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'success',
                                            "部署成功，服务正常运行",
                                            java_healthy=health_result.get('java_healthy', False),
                                            cpp_healthy=health_result.get('cpp_healthy', False))
                    success_count += 1
                else:
                    task.log_content += f"健康检查失败: {health_result['message']}\n"
                    task.save()
                    record_deployment_history(task, vm_relation, 'failed',
                                            f"健康检查失败: {health_result['message']}")
                    fail_count += 1
                    
            except Exception as e:
                import traceback
                error_msg = traceback.format_exc()
                task.log_content += f"部署过程异常: {error_msg}\n"
                task.save()
                record_deployment_history(task, vm_relation, 'failed', f"部署异常: {str(e)}")
                fail_count += 1
            
            # 更新进度
            task.progress = int((i + 1) / total_vms * 100)
            task.save()
        
        # 更新任务状态
        if fail_count == 0:
            task.status = 'success'
            task.log_content += f"\n=== 所有虚拟机部署成功！ ===\n"
        else:
            task.status = 'failed' if success_count == 0 else 'partial'
            task.log_content += f"\n=== 部署完成，成功: {success_count}, 失败: {fail_count} ===\n"
        
        task.completed_at = timezone.now()
        task.save()
        
        # 清理临时文件
        try:
            if os.path.exists(package.file_path):
                os.remove(package.file_path)
        except:
            pass
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        task.log_content += f"任务执行异常: {error_msg}\n"
        task.status = 'failed'
        task.completed_at = timezone.now()
        task.save()


def upload_file_to_server(vm_relation, package):
    """上传文件到服务器（使用SCP协议）"""
    import paramiko
    from scp import SCPClient
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        target_ip = vm_relation.get_ip()
        ssh_port = vm_relation.ssh_port
        ssh_username = vm_relation.ssh_username
        ssh_password = vm_relation.ssh_password
        ssh_key_path = vm_relation.ssh_key_path
        
        # 连接服务器
        if ssh_key_path and os.path.exists(ssh_key_path):
            ssh.connect(target_ip, port=ssh_port,
                       username=ssh_username,
                       key_filename=ssh_key_path,
                       timeout=30)
        else:
            ssh.connect(target_ip, port=ssh_port,
                       username=ssh_username,
                       password=ssh_password,
                       timeout=30)
        
        # 创建目标目录
        ssh.exec_command('mkdir -p /opt')
        
        # 上传文件
        with SCPClient(ssh.get_transport()) as scp:
            remote_path = f"/opt/{os.path.basename(package.file_path)}"
            scp.put(package.file_path, remote_path)
        
        # 设置权限
        ssh.exec_command(f'chmod +x {remote_path}')
        
        ssh.close()
        
        return {'success': True, 'remote_path': remote_path}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def execute_deployment_script(vm_relation, script_content):
    """在远程服务器上执行部署脚本（修复换行符问题）"""
    import paramiko
    import os
    import time
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        target_ip = vm_relation.get_ip()
        ssh_port = vm_relation.ssh_port or 22
        ssh_username = vm_relation.ssh_username or 'root'
        ssh_password = vm_relation.ssh_password
        ssh_key_path = vm_relation.ssh_key_path
        
        # 连接超时时间
        timeout = 30
        
        # 连接服务器
        if ssh_key_path and os.path.exists(ssh_key_path):
            ssh.connect(target_ip, port=ssh_port,
                       username=ssh_username,
                       key_filename=ssh_key_path,
                       timeout=timeout)
        else:
            ssh.connect(target_ip, port=ssh_port,
                       username=ssh_username,
                       password=ssh_password,
                       timeout=timeout)
        
        # 首先检查/opt目录下有哪些文件
        stdin, stdout, stderr = ssh.exec_command('ls -la /opt/')
        opt_files = stdout.read().decode('utf-8', errors='ignore')
        print(f"服务器 {target_ip} 的 /opt/ 目录文件列表:\n{opt_files}")
        
        # 将脚本写入临时文件
        script_file = f"/tmp/deploy_script_{int(time.time())}.sh"
        
        # 🔥 修复：二进制模式写入，避免换行符转换
        sftp = ssh.open_sftp()
        with sftp.file(script_file, 'wb') as f:   # 改为 'wb'
            f.write(script_content.encode('utf-8'))  # 写入字节数据
        sftp.chmod(script_file, 0o755)
        sftp.close()
        
        # 执行脚本（增加超时时间）
        command = f'sudo bash {script_file}'
        print(f"执行部署脚本: {command}")
        stdin, stdout, stderr = ssh.exec_command(command, timeout=300)  # 5分钟超时
        
        # 获取输出
        output = stdout.read().decode('utf-8', errors='ignore')
        error = stderr.read().decode('utf-8', errors='ignore')
        
        # 获取退出码
        exit_status = stdout.channel.recv_exit_status()
        
        print(f"脚本执行结果 - 退出码: {exit_status}")
        if output:
            print(f"标准输出 (前500字符): {output[:500]}...")
        if error:
            print(f"标准错误: {error}")
        
        # 清理临时文件
        ssh.exec_command(f'rm -f {script_file}')
        ssh.close()
        
        return {
            'success': exit_status == 0,
            'output': output,
            'error': error,
            'exit_status': exit_status
        }
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"执行部署脚本异常: {str(e)}")
        print(f"详细错误: {error_msg}")
        return {
            'success': False,
            'output': '',
            'error': str(e),
            'exit_status': -1
        }


def perform_health_check(vm_relation, project):
    """执行健康检查（基于端口判断）"""
    import socket
    
    target_ip = vm_relation.get_ip()
    java_port = project.java_port or 8080
    cpp_port = project.cpp_port or 8000
    timeout = project.health_check_timeout or 10
    
    try:
        results = {
            'success': True,
            'message': '',
            'java_healthy': False,
            'cpp_healthy': False
        }
        
        # 检查Java端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        java_result = sock.connect_ex((target_ip, java_port))
        results['java_healthy'] = (java_result == 0)
        sock.close()
        
        # 检查C++端口
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        cpp_result = sock.connect_ex((target_ip, cpp_port))
        results['cpp_healthy'] = (cpp_result == 0)
        sock.close()
        
        # 简化健康检查逻辑：只要有一个端口正常就算成功
        # 或者根据你的实际需求调整逻辑
        
        # 方案1：只要有一个端口正常就算成功（适用于大多数情况）
        if results['java_healthy'] or results['cpp_healthy']:
            healthy_services = []
            if results['java_healthy']:
                healthy_services.append('Java')
            if results['cpp_healthy']:
                healthy_services.append('C++')
            results['message'] = f"{'和'.join(healthy_services)} 服务端口正常"
            results['success'] = True
        else:
            results['message'] = f'所有服务端口异常(Java:{java_port}, C++:{cpp_port})'
            results['success'] = False
        
        # 方案2：两个端口都必须正常（如果你需要严格要求）
        # if results['java_healthy'] and results['cpp_healthy']:
        #     results['message'] = '所有服务端口正常'
        #     results['success'] = True
        # else:
        #     error_details = []
        #     if not results['java_healthy']:
        #         error_details.append(f'Java服务端口 {java_port} 不可达')
        #     if not results['cpp_healthy']:
        #         error_details.append(f'C++服务端口 {cpp_port} 不可达')
        #     results['message'] = '; '.join(error_details)
        #     results['success'] = False
        
        return results
        
    except socket.timeout:
        return {
            'success': False,
            'message': f'连接超时（{timeout}秒）',
            'java_healthy': False,
            'cpp_healthy': False
        }
    except socket.error as e:
        return {
            'success': False,
            'message': f'连接错误: {str(e)}',
            'java_healthy': False,
            'cpp_healthy': False
        }
    except Exception as e:
        return {
            'success': False,
            'message': f'健康检查异常: {str(e)}',
            'java_healthy': False,
            'cpp_healthy': False
        }


def record_deployment_history(task, vm_relation, status, message, 
                            java_healthy=False, cpp_healthy=False):
    """记录部署历史"""
    from django.utils import timezone
    
    start_time = task.started_at
    end_time = timezone.now()
    duration = int((end_time - start_time).total_seconds())
    
    # 获取脚本内容
    try:
        script = task.project.deployment_script
        script_content = script.content
    except:
        script_content = get_default_deployment_script(task.project)
    
    DeploymentHistory.objects.create(
        task=task,
        project_vm=vm_relation,
        package_version=task.package.version,
        script_content=script_content,
        status=status,
        message=message,
        java_service_healthy=java_healthy,
        cpp_service_healthy=cpp_healthy,
        error_message=message if status == 'failed' else '',
        started_at=start_time,
        completed_at=end_time,
        duration=duration
    )

def get_default_deployment_script(project):
    """获取默认部署脚本"""
    # 使用原始字符串避免转义问题
    script_template = r'''#!/bin/bash

# ============================================
# 自动部署脚本 - {project_name}
# 生成时间: {timestamp}
# ============================================

# 项目配置参数（自动替换）
UPBAKDIR="{backup_path}"
DCSDIR="{cpp_install_path}"
TOMCATDIR="{java_install_path}"

# 从配置文件读取数据库信息
dcsconfig_file="${{DCSDIR}}/config/config.conf"

if [ -f "$dcsconfig_file" ]; then
    DBHOST_IP=$(sed '/^Host=/!d;s/.*=//' $dcsconfig_file | sed -e 's/\r//g')
    DBPORT=$(sed '/^Port=/!d;s/.*=//' $dcsconfig_file | sed -e 's/\r//g')
    DBUSERNAME=$(sed '/^Username=/!d;s/.*=//' $dcsconfig_file | sed -e 's/\r//g')
    DBPASSWORD=$(sed '/^Password=/!d;s/.*Password=//' $dcsconfig_file | sed -e 's/\r//g')
    DBDATABASE=$(sed '/^Database=/!d;s/.*=//' $dcsconfig_file | sed -e 's/\r//g')
else
    echo "警告: 未找到配置文件 $dcsconfig_file"
    DBHOST_IP=""
    DBPORT=""
    DBUSERNAME=""
    DBPASSWORD=""
    DBDATABASE=""
fi

DATE=`date +"%Y%m%d%H%M"`

mkdir -p ${{UPBAKDIR}}/$DATE/up/java/
mkdir -p ${{UPBAKDIR}}/$DATE/bak/java/
mkdir -p ${{UPBAKDIR}}/$DATE/up/H5/
mkdir -p ${{UPBAKDIR}}/$DATE/bak/H5/
mkdir -p ${{UPBAKDIR}}/$DATE/up/dcs/
mkdir -p ${{UPBAKDIR}}/$DATE/bak/dcs/

# 备份数据库
if [ ! -z "$DBHOST_IP" ] && [ ! -z "$DBUSERNAME" ]; then
    echo "开始备份数据库..."
    # 创建临时MySQL配置文件，避免命令行密码警告
    MYSQL_CNF=$(mktemp /tmp/mysql_backup.cnf.XXXXXX)
    chmod 600 $MYSQL_CNF
    cat > $MYSQL_CNF << EOF
[client]
host = $DBHOST_IP
port = $DBPORT
user = $DBUSERNAME
password = $DBPASSWORD
EOF
    
    # 使用配置文件进行备份
    /usr/local/PCMS/mysql/bin/mysqldump --defaults-extra-file=$MYSQL_CNF \
        --databases $DBDATABASE \
        --single-transaction \
        --set-gtid-purged=off \
        --hex-blob \
        > ${{UPBAKDIR}}/$DATE/bak/pcms.sql
    
    # 清理临时配置文件
    rm -f $MYSQL_CNF
    
    # 检查备份文件大小
    BACKUP_FILE="${{UPBAKDIR}}/$DATE/bak/pcms.sql"
    if [ -s "$BACKUP_FILE" ]; then
        echo "数据库备份完成: $BACKUP_FILE"
        echo "备份文件大小: $(du -h $BACKUP_FILE | cut -f1)"
    else
        echo "警告: 数据库备份文件为空或不存在"
    fi
else
    echo "警告: 数据库信息不完整，跳过数据库备份"
fi


echo "进入更新java全量版本步骤……"
if [ -f /opt/pcms.war ];then
    echo "开始更新java全量"
    echo "创建更新与备份文件夹"

    echo "移动更新文件至更新文件夹"
    mv /opt/pcms.war ${{UPBAKDIR}}/$DATE/up/java/
    
	echo "停止watch服务"
	systemctl stop watch_pcms.service

    echo "停止tomcat服务"
	systemctl stop tomcat.service
    sleep 2
    
    while true
    do
        ST=`ps -C tomcat --no-header |wc -l`
        if [ $ST -eq 0 ];then
            break
        else
            sleep 2
			systemctl stop tomcat.service
        fi
    done
    
    echo "备份版本"
    mv ${{TOMCATDIR}}/webapps/pcms/ ${{UPBAKDIR}}/$DATE/bak/java/

    if [ -f ${{TOMCATDIR}}/webapps/pcms.war ];then
        mv ${{TOMCATDIR}}/webapps/pcms.war ${{UPBAKDIR}}/$DATE/bak/java/
    fi

    echo "更新版本"
    cp ${{UPBAKDIR}}/$DATE/up/java/pcms.war ${{TOMCATDIR}}/webapps/

    echo "更换许可与配置文件"
	systemctl start tomcat.service
    sleep 10
	systemctl stop tomcat.service
    /bin/cp ${{UPBAKDIR}}/$DATE/bak/java/pcms/license/pcmsLicense.li ${{TOMCATDIR}}/webapps/pcms/license/
    /bin/cp ${{UPBAKDIR}}/$DATE/bak/java/pcms/WEB-INF/classes/config/property/* ${{TOMCATDIR}}/webapps/pcms/WEB-INF/classes/config/property/
    
    echo "获取原版本会议室图片和轮播图等文件"
    rm -rf ${{TOMCATDIR}}/webapps/pcms/roomPicture/
    rm -rf ${{TOMCATDIR}}/webapps/pcms/upload/
    /bin/cp -r ${{UPBAKDIR}}/$DATE/bak/java/pcms/roomPicture/ ${{TOMCATDIR}}/webapps/pcms/
    /bin/cp -r ${{UPBAKDIR}}/$DATE/bak/java/pcms/upload/ ${{TOMCATDIR}}/webapps/pcms/

    echo "删除缓存文件"
    rm -rf ${{TOMCATDIR}}/work/Catalina/
    
    echo "启动tomcat服务"
	systemctl restart tomcat.service

	echo "启动watch服务"
	systemctl restart watch_pcms.service
else
    echo "未检测到java全量更新版本"
fi

echo "进入更新java增量版本步骤……"
if [ -f /opt/pcms.zip ];then
    echo "开始更新java增量"
    echo "解压zip增量包"
    unzip /opt/pcms.zip -d ${{UPBAKDIR}}/$DATE/up/java/
    rm -f /opt/pcms.zip
    
	echo "停止watch服务"
	systemctl stop watch_pcms.service

    echo "停止tomcat服务"
	systemctl stop tomcat.service
    sleep 2
    
    while true
    do
        ST=`ps -C tomcat --no-header |wc -l`
        if [ $ST -eq 0 ];then
            break
        else
            sleep 2
			systemctl stop tomcat.service
        fi
    done
    
    echo "备份版本"
    cp -r ${{TOMCATDIR}}/webapps/pcms/ ${{UPBAKDIR}}/$DATE/bak/java/

    if [ -f ${{TOMCATDIR}}/webapps/pcms.war ];then
        mv ${{TOMCATDIR}}/webapps/pcms.war ${{UPBAKDIR}}/$DATE/bak/java/
    fi

    echo "更新版本"
    /bin/cp -r ${{UPBAKDIR}}/$DATE/up/java/pcms/ ${{TOMCATDIR}}/webapps/

    echo "更换许可与配置文件"
	systemctl start tomcat.service
    sleep 5
    /bin/cp ${{UPBAKDIR}}/$DATE/bak/java/pcms/license/pcmsLicense.li ${{TOMCATDIR}}/webapps/pcms/license/
    /bin/cp ${{UPBAKDIR}}/$DATE/bak/java/pcms/WEB-INF/classes/config/property/* ${{TOMCATDIR}}/webapps/pcms/WEB-INF/classes/config/property/

    echo "获取原版本会议室图片和轮播图等文件"
    rm -rf ${{TOMCATDIR}}/webapps/pcms/roomPicture/
    rm -rf ${{TOMCATDIR}}/webapps/pcms/upload/
    /bin/cp -r ${{UPBAKDIR}}/$DATE/bak/java/pcms/roomPicture/ ${{TOMCATDIR}}/webapps/pcms/
    /bin/cp -r ${{UPBAKDIR}}/$DATE/bak/java/pcms/upload/ ${{TOMCATDIR}}/webapps/pcms/

    echo "删除缓存文件"
    rm -rf ${{TOMCATDIR}}/work/Catalina/
    
    echo "启动服务"
	systemctl restart tomcat.service

	echo "启动watch服务"
	systemctl start watch_pcms.service
else
    echo "未检测到java增量更新版本"
fi

echo "进入更新H5版本步骤……"
if [ -f /opt/confApp.zip ];then
    echo "开始更新H5"
    echo "解压zip增量包"
    unzip /opt/confApp.zip -d ${{UPBAKDIR}}/$DATE/up/H5/
    rm -f /opt/confApp.zip
    
	echo "停止watch服务"
	systemctl stop watch_pcms.service

    echo "停止tomcat服务"
	systemctl stop tomcat.service
    sleep 2
    
    while true
    do
        ST=`ps -C tomcat --no-header |wc -l`
        if [ $ST -eq 0 ];then
            break
        else
            sleep 2
			systemctl stop tomcat.service
        fi
    done
    
    echo "备份版本"
    mv ${{TOMCATDIR}}/webapps/confApp/ ${{UPBAKDIR}}/$DATE/bak/H5/

    echo "更新版本"
    /bin/cp -r ${{UPBAKDIR}}/$DATE/up/H5/confApp/ ${{TOMCATDIR}}/webapps/

    echo "删除缓存文件"
    rm -rf ${{TOMCATDIR}}/work/Catalina/
    
    echo "启动服务"
	systemctl restart tomcat.service

	echo "启动watch服务"
	systemctl sttart watch_pcms.service
else
    echo "未检测到H5更新版本"
fi

echo "进入更新javapcmsLog全量版本步骤……"
if [ -f /opt/pcmsLog.war ];then
    echo "开始更新javapcmsLog全量"
    echo "移动更新文件至更新文件夹"
    mv /opt/pcmsLog.war ${{UPBAKDIR}}/$DATE/up/java/
    
	echo "停止watch服务"
	systemctl stop watch_pcms.service

    echo "停止tomcat服务"
	systemctl stop tomcat.service
    sleep 2
    
    while true
    do
        ST=`ps -C tomcat --no-header |wc -l`
        if [ $ST -eq 0 ];then
            break
        else
            sleep 2
            systemctl stop tomcat.service
        fi
    done
    
    echo "备份版本"
    mv ${{TOMCATDIR}}/webapps/pcmsLog/ ${{UPBAKDIR}}/$DATE/bak/java/

    if [ -f ${{TOMCATDIR}}/webapps/pcmsLog.war ];then
        mv ${{TOMCATDIR}}/webapps/pcmsLog.war ${{UPBAKDIR}}/$DATE/bak/java/
    fi

    echo "更新版本"
    cp ${{UPBAKDIR}}/$DATE/up/java/pcmsLog.war ${{TOMCATDIR}}/webapps/

    echo "更换配置文件"
    systemctl start tomcat.service
    sleep 10
    systemctl stop tomcat.service
    /bin/cp ${{UPBAKDIR}}/$DATE/bak/java/pcmsLog/WEB-INF/classes/config/property/* ${{TOMCATDIR}}/webapps/pcmsLog/WEB-INF/classes/config/property/

    echo "删除缓存文件"
    rm -rf ${{TOMCATDIR}}/work/Catalina/
    
    echo "启动服务"
    systemctl restart tomcat.service

	echo "停止watch服务"
	systemctl start watch_pcms.service
else
    echo "未检测到javapcmsLog全量更新版本"
fi

echo "进入更新javapcmsLog增量版本步骤……"
if [ -f /opt/pcmsLog.zip ];then
    echo "开始更新javapcmsLog增量"
    echo "解压zip增量包"
    unzip /opt/pcmsLog.zip -d ${{UPBAKDIR}}/$DATE/up/java/
    rm -f /opt/pcmsLog.zip
    
	echo "停止watch服务"
	systemctl stop watch_pcms.service

    echo "停止tomcat服务"
    systemctl stop tomcat.service
    sleep 2
    
    while true
    do
        ST=`ps -C tomcat --no-header |wc -l`
        if [ $ST -eq 0 ];then
            break
        else
            sleep 2
            systemctl stop tomcat.service
        fi
    done
    
    echo "备份版本"
    cp -r ${{TOMCATDIR}}/webapps/pcmsLog/ ${{UPBAKDIR}}/$DATE/bak/java/

    if [ -f ${{TOMCATDIR}}/webapps/pcmsLog.war ];then
        mv ${{TOMCATDIR}}/webapps/pcmsLog.war ${{UPBAKDIR}}/$DATE/bak/java/
    fi

    echo "更新版本"
    /bin/cp -r ${{UPBAKDIR}}/$DATE/up/java/pcmsLog/ ${{TOMCATDIR}}/webapps/
    
    echo "更换配置文件"
    systemctl start tomcat.service
    sleep 10
    systemctl stop tomcat.service
    /bin/cp ${{UPBAKDIR}}/$DATE/bak/java/pcmsLog/WEB-INF/classes/config/property/* ${{TOMCATDIR}}/webapps/pcmsLog/WEB-INF/classes/config/property/

    echo "删除缓存文件"
    rm -rf ${{TOMCATDIR}}/work/Catalina/
    
    echo "启动服务"
    systemctl restart tomcat.service

	echo "启动watch服务"
	systemctl start watch_pcms.service
else
    echo "未检测到javapcmsLog增量更新版本"
fi

echo "进入更新dcs版本步骤……"
if [ -f /opt/pcms ];then
    echo "开始更新dcs"
    echo "移动更新文件至更新文件夹"
    mv /opt/pcms ${{UPBAKDIR}}/$DATE/up/dcs/
    
	echo "停止watch服务"
	systemctl stop watch_pcms.service

    echo "停止pcms服务"
    systemctl stop pcms.service
    sleep 2
    
    while true
    do
        SP=`ps -C pcms --no-header |wc -l`
        if [ $SP -eq 0 ];then
            break
        else
            sleep 2
            systemctl stop pcms.service
        fi
    done

    echo "备份版本"
    mv ${{DCSDIR}}/pcms ${{UPBAKDIR}}/$DATE/bak/dcs/
    
    echo "更新版本"
    cp ${{UPBAKDIR}}/$DATE/up/dcs/pcms ${{DCSDIR}}
    chmod 777 ${{DCSDIR}}/pcms

    echo "启动服务"
    systemctl start pcms.service

	echo "启动watch服务"
	systemctl start watch_pcms.service
else
    echo "未发现dcs更新文件"
fi

echo "=== 部署完成 ==="
echo "检查服务状态..."
sleep 5

# 健康检查
echo "执行健康检查..."
echo "1. 检查Java服务（端口: {java_port}）..."
if nc -z localhost {java_port}; then
    echo "✓ Java服务端口 {java_port} 正常"
    JAVA_HEALTHY=1
else
    echo "✗ Java服务端口 {java_port} 异常"
    JAVA_HEALTHY=0
fi

echo "2. 检查C++服务（端口: {cpp_port}）..."
if nc -z localhost {cpp_port}; then
    echo "✓ C++服务端口 {cpp_port} 正常"
    CPP_HEALTHY=1
else
    echo "✗ C++服务端口 {cpp_port} 异常"
    CPP_HEALTHY=0
fi

# 汇总结果
if [ $JAVA_HEALTHY -eq 1 ] && [ $CPP_HEALTHY -eq 1 ]; then
    echo "✓ 所有服务端口检查正常"
    EXIT_CODE=0
else
    echo "✗ 部分服务端口异常"
    EXIT_CODE=1
fi

echo "=== 部署脚本执行结束 ==="
exit $EXIT_CODE
'''
    
    # 获取当前时间戳
    from django.utils import timezone
    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # 替换模板中的变量
    script = script_template.format(
        project_name=project.name,
        timestamp=timestamp,
        backup_path=project.backup_path,
        cpp_install_path=project.cpp_install_path,
        java_install_path=project.java_install_path,
        java_port=project.java_port,
        cpp_port=project.cpp_port
    )
    
    return script

@login_required
def package_list(request):
    """包列表"""
    packages = DeploymentPackage.objects.filter(is_active=True).order_by('-uploaded_at')
    
    # 搜索功能
    search_query = request.GET.get('q', '')
    package_type = request.GET.get('type', '')
    
    if search_query:
        packages = packages.filter(
            Q(name__icontains=search_query) |
            Q(version__icontains=search_query) |
            Q(description__icontains=search_query)  # 修复这里
        )
    
    if package_type:
        packages = packages.filter(package_type=package_type)
    
    # 分页
    paginator = Paginator(packages, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'package_type': package_type,
    }
    return render(request, 'kb/deployment/package_list.html', context)


@login_required
@require_deployment_models
def task_list(request):
    """任务列表"""
    tasks = DeploymentTask.objects.all().order_by('-created_at')
    
    # 搜索功能
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    project_id = request.GET.get('project', '')
    
    if search_query:
        tasks = tasks.filter(
            Q(name__icontains=search_query) |
            Q(task_id__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    if project_id:
        tasks = tasks.filter(project_id=project_id)
    
    # 计算统计数据 - 使用过滤后的任务集
    total_count = tasks.count()
    deploying_count = tasks.filter(
        Q(status='deploying') | Q(status='uploading')
    ).count()
    success_count = tasks.filter(status='success').count()
    failed_count = tasks.filter(status='failed').count()
    
    # 分页
    paginator = Paginator(tasks, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取项目列表用于筛选
    projects = Project.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'project_id': project_id,
        'projects': projects,
        # 添加统计数据
        'total_count': total_count,
        'deploying_count': deploying_count,
        'success_count': success_count,
        'failed_count': failed_count,
    }
    return render(request, 'kb/deployment/task_list.html', context)


@login_required
@require_deployment_models
def task_detail(request, pk):
    """任务详情"""
    task = get_object_or_404(DeploymentTask, pk=pk)
    
    context = {
        'task': task,
    }
    return render(request, 'kb/deployment/task_detail.html', context)


@login_required
@require_deployment_models
def task_progress(request, pk):
    """获取任务进度"""
    task = get_object_or_404(DeploymentTask, pk=pk)
    
    return JsonResponse({
        'task_status': task.status,
        'task_progress': task.progress,
        'log_content': task.log_content[-5000:] if task.log_content else '',  # 返回最后5000字符
    })


@login_required
@require_deployment_models
def history_list(request):
    """历史记录列表 - 简化版"""
    from .models import DeploymentHistory
    
    # 获取所有历史记录，按完成时间倒序排列
    histories = DeploymentHistory.objects.all().order_by('-completed_at')
    
    # 搜索功能 - 按项目名称筛选
    search_query = request.GET.get('q', '')
    if search_query:
        histories = histories.filter(
            Q(task__project__name__icontains=search_query) |
            Q(project_vm__virtual_machine__name__icontains=search_query)
        )
    
    # 按时间筛选
    date_filter = request.GET.get('date', '')
    if date_filter:
        histories = histories.filter(completed_at__date=date_filter)
    
    # 按项目筛选
    project_id = request.GET.get('project', '')
    if project_id:
        histories = histories.filter(task__project_id=project_id)
    
    # 分页 - 每页10条
    paginator = Paginator(histories, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 获取所有项目用于筛选下拉框
    from .models import Project
    projects = Project.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'date_filter': date_filter,
        'project_id': project_id,
        'projects': projects,
    }
    return render(request, 'kb/deployment/history_list.html', context)


@login_required
@require_deployment_models
def history_detail(request, pk):
    """历史记录详情"""
    from .models import DeploymentHistory
    
    history = get_object_or_404(DeploymentHistory, pk=pk)
    
    context = {
        'history': history,
    }
    return render(request, 'kb/deployment/history_detail.html', context)


@login_required
@require_GET
@require_deployment_models
def vm_search_api(request):
    """虚拟机搜索API"""
    query = request.GET.get('q', '')
    limit = request.GET.get('limit', 10)
    
    if not query:
        return JsonResponse({'results': []})
    
    try:
        # 搜索虚拟机
        vms = VirtualMachine.objects.filter(
            Q(name__icontains=query) |
            Q(ip_address__icontains=query) |
            Q(host_machine__name__icontains=query)  # 修复这里的语法
        ).select_related('host_machine')
        
        # 限制返回数量
        vms = vms[:int(limit)]
        
        results = []
        for vm in vms:
            results.append({
                'id': vm.id,
                'name': vm.name,
                'ip_address': vm.ip_address,
                'host_name': vm.host_machine.name if vm.host_machine else '',
                'host_machine': vm.host_machine.name if vm.host_machine else '',
                'status': vm.status,
                'status_display': vm.get_status_display(),
                'os': vm.get_os_display(),
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        logger.error(f"虚拟机搜索失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'搜索失败: {str(e)}',
            'results': []
        }, status=500)


@login_required
@require_GET
@require_deployment_models
def project_vm_status_api(request, pk):
    """获取项目虚拟机状态API"""
    try:
        project = Project.objects.get(pk=pk)
        vm_relations = project.projectvmrelation_set.select_related('virtual_machine')
        
        vm_status_list = []
        total_count = 0
        healthy_count = 0
        
        for relation in vm_relations:
            vm = relation.virtual_machine
            target_ip = relation.get_ip()
            
            # 检查虚拟机状态
            is_healthy = vm.status == 'running'
            if is_healthy:
                healthy_count += 1
            total_count += 1
            
            vm_status_list.append({
                'id': vm.id,
                'name': vm.name,
                'ip': target_ip,
                'status': vm.status,
                'status_display': vm.get_status_display(),
                'is_healthy': is_healthy,
                'host': vm.host_machine.name if vm.host_machine else '',
                'ssh_username': relation.ssh_username,
                'ssh_port': relation.ssh_port,
            })
        
        return JsonResponse({
            'success': True,
            'project_id': project.id,
            'project_name': project.name,
            'total_vms': total_count,
            'healthy_vms': healthy_count,
            'vm_status_list': vm_status_list,
        })
        
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'获取项目虚拟机状态失败: {str(e)}'
        }, status=500)


@login_required
@require_GET
def vm_detail_api(request, pk):
    """获取虚拟机详细信息 API"""
    try:
        vm = get_object_or_404(VirtualMachine, pk=pk)
        
        return JsonResponse({
            'success': True,
            'id': vm.id,
            'name': vm.name,
            'ip_address': vm.ip_address,
            'host_name': vm.host_machine.name if vm.host_machine else '',
            'host_machine': vm.host_machine.name if vm.host_machine else '',
            'status': vm.status,
            'status_display': vm.get_status_display(),
            'os': vm.get_os_display(),
            'cpu': vm.cpu,
            'memory': vm.memory,
            'disk': vm.disk,
            'owner': vm.owner.username if vm.owner else None,
        })
    except Exception as e:
        logger.error(f"获取虚拟机详情失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'获取虚拟机信息失败: {str(e)}'
        }, status=500)


@login_required
@require_GET
@require_deployment_models
def task_detail_api(request, pk):
    """获取任务详情API"""
    try:
        task = DeploymentTask.objects.get(pk=pk)
        
        # 获取部署结果
        results = DeploymentResult.objects.filter(task=task)
        results_data = []
        for result in results:
            results_data.append({
                'vm_name': result.vm.name if result.vm else '',
                'ip_address': result.vm.ip_address if result.vm else '',
                'status': result.status,
                'status_display': result.get_status_display(),
                'java_healthy': result.java_healthy,
                'cpp_healthy': result.cpp_healthy,
                'duration': result.duration or 0,
            })
        
        # 状态对应的CSS类
        status_classes = {
            'pending': 'secondary',
            'uploading': 'info',
            'deploying': 'warning',
            'success': 'success',
            'failed': 'danger',
            'partial': 'info',
            'cancelled': 'secondary'
        }
        
        task_data = {
            'task_id': task.task_id,
            'name': task.name,
            'project_name': task.project.name if task.project else '',
            'package_version': task.package_version or '',
            'status': task.status,
            'status_display': task.get_status_display(),
            'status_class': status_classes.get(task.status, 'secondary'),
            'progress': task.progress,
            'created_at': task.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else None,
            'log_content': task.log_content or '',
        }
        
        return JsonResponse({
            'success': True,
            'task': task_data,
            'results': results_data
        })
        
    except DeploymentTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)

@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def tasks_status_api(request):
    """批量获取任务状态API"""
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        
        tasks = DeploymentTask.objects.filter(id__in=task_ids)
        tasks_data = []
        
        for task in tasks:
            tasks_data.append({
                'id': task.id,
                'task_id': task.task_id,
                'name': task.name,
                'status': task.status,
                'status_display': task.get_status_display(),
                'progress': task.progress,
            })
        
        return JsonResponse({
            'success': True,
            'tasks': tasks_data
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)

@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def tasks_delete_api(request):
    """批量删除任务API"""
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return JsonResponse({
                'success': False,
                'message': '未选择任务'
            })
        
        # 检查是否可以删除（不能删除进行中的任务）
        tasks = DeploymentTask.objects.filter(id__in=task_ids)
        
        # 检查是否有进行中的任务
        active_tasks = tasks.filter(
            Q(status='deploying') | Q(status='uploading')
        )
        
        if active_tasks.exists():
            return JsonResponse({
                'success': False,
                'message': '无法删除进行中的任务，请先取消或等待完成'
            })
        
        # 删除任务
        deleted_count, _ = tasks.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'成功删除 {deleted_count} 个任务',
            'deleted_count': deleted_count
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)

@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def task_start_api(request, pk):
    """开始任务API"""
    try:
        task = DeploymentTask.objects.get(pk=pk)
        
        # 检查任务状态
        if task.status not in ['pending', 'uploaded']:
            return JsonResponse({
                'success': False,
                'message': '任务当前状态无法开始'
            })
        
        # 更新任务状态
        task.status = 'deploying'
        task.started_at = timezone.now()
        task.save()
        
        # 异步执行部署任务
        import threading
        thread = threading.Thread(target=execute_deployment_task, args=(task.pk,))
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            'success': True,
            'message': '任务已开始执行'
        })
        
    except DeploymentTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"开始任务失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'开始任务失败: {str(e)}'
        }, status=500)

@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def task_cancel_api(request, pk):
    """取消任务API"""
    try:
        task = DeploymentTask.objects.get(pk=pk)
        
        # 检查任务状态
        if task.status not in ['deploying', 'uploading']:
            return JsonResponse({
                'success': False,
                'message': '任务当前状态无法取消'
            })
        
        # 更新任务状态
        task.status = 'cancelled'
        task.completed_at = timezone.now()
        task.save()
        
        # 记录日志
        if task.log_content:
            task.log_content += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务已取消\n"
        else:
            task.log_content = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务已取消\n"
        task.save()
        
        return JsonResponse({
            'success': True,
            'message': '任务已取消'
        })
        
    except DeploymentTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"取消任务失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'取消任务失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def task_retry_api(request, pk):
    """重试任务API"""
    try:
        task = DeploymentTask.objects.get(pk=pk)
        
        # 检查任务状态
        if task.status not in ['failed', 'partial']:
            return JsonResponse({
                'success': False,
                'message': '只有失败或部分成功的任务可以重试'
            })
        
        # 重置任务状态
        task.status = 'pending'
        task.progress = 0
        task.started_at = None
        task.completed_at = None
        
        # 清除旧的部署历史
        DeploymentHistory.objects.filter(task=task).delete()
        
        # 记录日志
        if task.log_content:
            task.log_content += f"\n[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务重置并准备重新执行\n"
        else:
            task.log_content = f"[{timezone.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务重置并准备重新执行\n"
        
        task.save()
        
        return JsonResponse({
            'success': True,
            'message': '任务已重置，请手动点击"开始部署"'
        })
        
    except DeploymentTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"重试任务失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'重试任务失败: {str(e)}'
        }, status=500)


@login_required
@require_GET
@require_deployment_models
def project_default_script_api(request, pk):
    """获取默认部署脚本API"""
    try:
        project = Project.objects.get(pk=pk)
        default_script = get_default_deployment_script(project)
        
        return JsonResponse({
            'success': True,
            'script_content': default_script,
            'message': '获取默认脚本成功'
        })
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"获取默认脚本失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'获取默认脚本失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def project_validate_script_api(request, pk):
    """验证部署脚本语法API"""
    try:
        import json
        data = json.loads(request.body)
        script_content = data.get('script', '')
        
        # 简单的bash语法检查
        import subprocess
        import tempfile
        
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(script_content)
            temp_file = f.name
        
        try:
            # 使用bash -n检查语法
            result = subprocess.run(
                ['bash', '-n', temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # 清理临时文件
            import os
            os.unlink(temp_file)
            
            if result.returncode == 0:
                return JsonResponse({
                    'success': True,
                    'message': '脚本语法验证通过'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '脚本语法验证失败',
                    'error': result.stderr
                })
                
        except subprocess.TimeoutExpired:
            os.unlink(temp_file)
            return JsonResponse({
                'success': False,
                'message': '脚本检查超时'
            })
        except Exception as e:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            return JsonResponse({
                'success': False,
                'message': f'检查过程中出错: {str(e)}'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"验证脚本失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'验证脚本失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def project_test_script_api(request, pk):
    """测试部署脚本API"""
    try:
        import json
        data = json.loads(request.body)
        vm_id = data.get('vm_id')
        script_content = data.get('script', '')
        dry_run = data.get('dry_run', True)
        
        # 获取项目
        project = Project.objects.get(pk=pk)
        
        # 获取虚拟机
        try:
            vm_relation = project.projectvmrelation_set.get(virtual_machine_id=vm_id)
        except ProjectVMRelation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '虚拟机不在项目中'
            })
        
        # 如果是干运行模式，只检查语法
        if dry_run:
            # 简单的语法检查
            import subprocess
            import tempfile
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
                # 在脚本开头添加dry run标记
                dry_run_script = f"#!/bin/bash\n# DRY RUN MODE - 只检查语法\n{script_content}"
                f.write(dry_run_script)
                temp_file = f.name
            
            try:
                result = subprocess.run(
                    ['bash', '-n', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                import os
                os.unlink(temp_file)
                
                if result.returncode == 0:
                    return JsonResponse({
                        'success': True,
                        'message': '干运行模式：脚本语法检查通过',
                        'output': '脚本语法正确，可以在远程服务器上执行'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '干运行模式：脚本语法检查失败',
                        'error': result.stderr
                    })
                    
            except subprocess.TimeoutExpired:
                os.unlink(temp_file)
                return JsonResponse({
                    'success': False,
                    'message': '脚本检查超时'
                })
            except Exception as e:
                if os.path.exists(temp_file):
                    os.unlink(temp_file)
                return JsonResponse({
                    'success': False,
                    'message': f'检查过程中出错: {str(e)}'
                })
        else:
            # 实际执行测试（这里可以简化，只执行一些安全命令）
            # 由于安全考虑，我们不建议在测试环境中执行完整脚本
            # 可以执行一个简单的echo命令来测试连接
            try:
                result = execute_remote_script(vm_relation, 'echo "测试连接成功！"')
                
                if result['success']:
                    return JsonResponse({
                        'success': True,
                        'message': '测试执行成功',
                        'output': result['output']
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '测试执行失败',
                        'error': result['error']
                    })
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'message': f'测试执行异常: {str(e)}'
                })
                
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"测试脚本失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'测试脚本失败: {str(e)}'
        }, status=500)


@login_required
@csrf_exempt
@require_POST
@require_deployment_models
def project_toggle_script_api(request, pk):
    """切换部署脚本启用状态API"""
    try:
        import json
        data = json.loads(request.body)
        active = data.get('active', False)
        
        project = Project.objects.get(pk=pk)
        
        try:
            script = project.deployment_script
            script.is_active = active
            script.save()
            
            return JsonResponse({
                'success': True,
                'message': f'脚本已{"启用" if active else "停用"}'
            })
        except DeploymentScript.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '项目没有部署脚本'
            })
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON数据'
        }, status=400)
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"切换脚本状态失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'切换脚本状态失败: {str(e)}'
        }, status=500)


@login_required
@require_GET
@require_deployment_models
def task_status_api(request, pk):
    """获取任务状态API"""
    try:
        task = DeploymentTask.objects.get(pk=pk)
        
        # 状态对应的CSS类
        status_classes = {
            'pending': 'secondary',
            'uploading': 'info',
            'deploying': 'warning',
            'success': 'success',
            'failed': 'danger',
            'partial': 'info',
            'cancelled': 'secondary'
        }
        
        # 获取最近的历史记录（用于操作历史部分）
        recent_history = task.deploymenthistory_set.all()[:5]
        history_data = []
        for history in recent_history:
            history_data.append({
                'vm_name': history.project_vm.virtual_machine.name,
                'status': history.status,
                'message': history.message,
                'completed_at': history.completed_at.strftime('%H:%M:%S') if history.completed_at else '',
                'duration': history.duration,
                'java_healthy': history.java_service_healthy,
                'cpp_healthy': history.cpp_service_healthy
            })
        
        task_data = {
            'success': True,
            'task': {
                'id': task.id,
                'task_id': task.task_id,
                'name': task.name,
                'status': task.status,
                'status_display': task.get_status_display(),
                'status_class': status_classes.get(task.status, 'secondary'),
                'progress': task.progress,
                'log_content': task.log_content or '',
                'completed_at': task.completed_at.strftime('%Y-%m-%d %H:%M:%S') if task.completed_at else None,
            },
            'history': history_data
        }
        
        return JsonResponse(task_data)
        
    except DeploymentTask.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '任务不存在'
        }, status=404)
    except Exception as e:
        logger.error(f"获取任务状态失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'获取任务状态失败: {str(e)}'
        }, status=500)


@login_required
@require_GET
@require_deployment_models
def project_search_api(request):
    """项目搜索API"""
    query = request.GET.get('q', '')
    limit = request.GET.get('limit', 10)
    
    if not query:
        return JsonResponse({'results': []})
    
    try:
        # 搜索项目
        projects = Project.objects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query)
        )
        
        # 限制返回数量
        projects = projects[:int(limit)]
        
        results = []
        for project in projects:
            # 获取项目虚拟机数量
            vm_count = project.projectvmrelation_set.count()
            
            results.append({
                'id': project.id,
                'name': project.name,
                'code': project.code,
                'description': project.description,
                'status': project.status,
                'vm_count': vm_count,
                'created_at': project.created_at.strftime('%Y-%m-%d') if project.created_at else '',
            })
        
        return JsonResponse({'results': results})
        
    except Exception as e:
        logger.error(f"项目搜索失败: {e}")
        return JsonResponse({
            'success': False,
            'message': f'搜索失败: {str(e)}',
            'results': []
        }, status=500)


@login_required
@require_GET
@require_deployment_models
def project_vm_health_check_api(request, pk):
    """检查项目虚拟机健康状况API"""
    try:
        project = Project.objects.get(pk=pk)
        vm_relations = project.projectvmrelation_set.select_related('virtual_machine')
        
        vm_status_list = []
        unhealthy_vms = []
        all_running = True
        
        for relation in vm_relations:
            vm = relation.virtual_machine
            target_ip = relation.get_ip()
            
            # 检查虚拟机状态
            is_running = vm.status == 'running'
            
            vm_info = {
                'id': vm.id,
                'name': vm.name,
                'ip': target_ip,
                'status': vm.status,
                'status_display': vm.get_status_display(),
                'is_running': is_running,
                'host': vm.host_machine.name if vm.host_machine else '',
            }
            
            vm_status_list.append(vm_info)
            
            if not is_running:
                all_running = False
                unhealthy_vms.append(vm_info)
        
        return JsonResponse({
            'success': True,
            'all_running': all_running,
            'total_vms': len(vm_status_list),
            'running_vms': len([v for v in vm_status_list if v['is_running']]),
            'unhealthy_vms': unhealthy_vms,
            'vm_status_list': vm_status_list,
        })
        
    except Project.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': '项目不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'检查虚拟机状态失败: {str(e)}'
        }, status=500)
