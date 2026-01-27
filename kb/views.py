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

# 添加 logger 定义
logger = logging.getLogger(__name__)

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


