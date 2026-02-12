from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from ckeditor.fields import RichTextField  # 富文本字段
# 使用 CKEditor 5
from django_ckeditor_5.fields import CKEditor5Field

# 自定义用户模型
class CustomUser(AbstractUser):
    # 角色选择
    ROLE_CHOICES = (
        ('admin', '管理员'),
        ('user', '普通用户'),
    )

    role = models.CharField('角色', max_length=20, choices=ROLE_CHOICES, default='user')
    department = models.CharField('部门', max_length=100, default='交付部')

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


# 2. 知识文章模型
class Article(models.Model):
    # 问题类型选择
    ARTICLE_TYPE_CHOICES = (
        ('product', '产品问题'),
        ('project', '项目问题'),
        ('network', '网络管理'),
        ('device', '设备使用'),
        ('package', '安装包制作'),
        ('test', '测试问题'),
        ('other', '其他'),
    )

    title = models.CharField('标题', max_length=200)
    #content = RichTextField('内容')  # 使用富文本字段，可以插入图片
    content = CKEditor5Field('内容', config_name='default')
    article_type = models.CharField('问题类型', max_length=20, choices=ARTICLE_TYPE_CHOICES, default='other')
    product_version = models.CharField('产品版本', max_length=100, blank=True, help_text='如：V3.0.1')
    project_name = models.CharField('项目名称', max_length=100, blank=True, help_text='定制项目名称')

    # 标签字段，可以用逗号分隔多个标签
    tags = models.CharField('标签', max_length=200, blank=True, help_text='用逗号分隔，如：网络,故障,紧急')

    # 关联作者
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='作者')

    # 统计字段
    views = models.IntegerField('浏览次数', default=0)
    is_resolved = models.BooleanField('是否解决', default=True)

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        ordering = ['-created_at']  # 按创建时间倒序排列
        verbose_name = '知识文章'
        verbose_name_plural = '知识文章'

    def __str__(self):
        return self.title

    def tag_list(self):
        """将标签字符串转换为列表"""
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',')]
        return []


# 3. 附件模型（支持截图和文件上传）
class Attachment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='attachments', verbose_name='所属文章')
    file = models.FileField('文件', upload_to='attachments/%Y/%m/%d/')
    file_name = models.CharField('文件名', max_length=200)
    file_type = models.CharField('文件类型', max_length=200)
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = '附件'
        verbose_name_plural = '附件'

    def __str__(self):
        return self.file_name

    def is_image(self):
        """判断是否为图片文件"""
        image_types = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']
        return self.file_type.split('/')[-1].lower() in image_types


# 4. 评论模型
class Comment(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name='comments', verbose_name='所属文章')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name='评论者')
    content = models.TextField('评论内容')
    created_at = models.DateTimeField('评论时间', auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = '评论'
        verbose_name_plural = '评论'

    def __str__(self):
        return f"{self.author.username} 在 {self.article.title} 的评论"


# 宿主机模型
class HostMachine(models.Model):
    STATUS_CHOICES = (
        ('normal', '运行正常'),
        ('fault', '运行故障'),
    )

    name = models.CharField('宿主机名称', max_length=100)
    ip_address = models.CharField('IP地址', max_length=50)
    location = models.CharField('位置', max_length=100, blank=True)
    username = models.CharField('用户名', max_length=50, blank=True)
    password = models.CharField('密码', max_length=50, blank=True)
    port = models.CharField('端口', max_length=20, blank=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='normal')
    last_check_time = models.DateTimeField('最后检查时间', null=True, blank=True)
    description = models.TextField('描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '宿主机'
        verbose_name_plural = '宿主机'

    def __str__(self):
        return f"{self.name} ({self.ip_address})"

    def get_status_color(self):
        """获取状态对应的颜色"""
        color_map = {
            'normal': 'success',
            'fault': 'danger',
        }
        return color_map.get(self.status, 'secondary')
    
    def get_vm_count(self):
        """获取宿主机上的虚拟机数量"""
        return self.virtual_machines.count()
    
    def get_vm_status_summary(self):
        """获取虚拟机状态摘要"""
        vms = self.virtual_machines.all()
        summary = {
            'total': vms.count(),
            'running': vms.filter(status='running').count(),
            'stopped': vms.filter(status='stopped').count(),
            'fault': vms.filter(status='fault').count(),
            'maintenance': vms.filter(status='maintenance').count(),
        }
        return summary

# 虚拟机模型
class VirtualMachine(models.Model):
    OS_CHOICES = (
        ('windows2003', 'Windows Server 2003'),
        ('windows2008', 'Windows Server 2008'),
        ('windows2012', 'Windows Server 2012'),
        ('windows2016', 'Windows Server 2016'),
        ('windows2016later', 'Windows Server 2016以后版本'),
        ('windows7', 'Windows 7'),
        ('windows10', 'Windows 10'),
        ('kylinv10x86', '麒麟V10_x86'),
        ('kylinv10arm', '麒麟V10_arm'),
        ('centos4/5', 'CentOS 4/5 或更早'),
        ('centos6', 'CentOS 6'),
        ('centos7', 'CentOS 7'),
        ('centos8', 'CentOS 8'),
        ('ubuntu', 'Ubuntu'),
        ('suse12', 'SUSE Linux 12'),
        ('coreos', 'CoreOS Linux'),
        ('debiangnu', 'Debian GNU Linux'),
        ('redhat', 'Red Hat'),
        ('other', '其他'),
    )

    STATUS_CHOICES = (
        ('running', '运行中'),
        ('stopped', '已停止'),
        ('maintenance', '维护中'),
        ('fault', '故障'),
    )

    name = models.CharField('虚拟机名称', max_length=100)
    ip_address = models.CharField('IP地址', max_length=50)
    host_machine = models.ForeignKey(HostMachine, on_delete=models.CASCADE,
                                     related_name='virtual_machines', verbose_name='所属宿主机')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, verbose_name='责任人')
    cpu = models.CharField('CPU配置', max_length=50)
    memory = models.CharField('内存配置', max_length=50)
    disk = models.CharField('磁盘配置', max_length=50)
    os = models.CharField('操作系统', max_length=50, choices=OS_CHOICES)
    os_version = models.CharField('系统版本', max_length=100, blank=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='running')
    purpose = models.TextField('用途描述', blank=True)
    notes = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '虚拟机'
        verbose_name_plural = '虚拟机'
        indexes = [
            models.Index(fields=['host_machine', 'status']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.ip_address})"
    
    def is_healthy(self):
        """检查虚拟机是否健康（非故障状态）"""
        return self.status != 'fault'
    
    def get_last_check_time(self):
        """获取最后一次检查时间"""
        return self.updated_at
    
    def get_status_info(self):
        """获取状态详细信息"""
        return {
            'name': self.name,
            'ip': self.ip_address,
            'status': self.get_status_display(),
            'is_healthy': self.is_healthy(),
            'last_check': self.updated_at,
            'host': self.host_machine.name,
        }


class Asset(models.Model):
    """资产管理模型"""

    ASSET_TYPE_CHOICES = (
        ('server', '服务器'),
        ('computer', '电脑'),
        ('video_terminal', '视频终端'),
        ('mcu', 'MCU'),
        ('smc', 'SMC'),
        ('maxhub', 'MAXHUB'),
        ('tv', '电视'),
        ('network_device', '网络设备'),
        ('storage', '存储设备'),
        ('phone', '手机平板'),
        ('monitor', '显示器'),
        ('other', '其他'),
    )

    STATUS_CHOICES = (
        ('in_use', '使用中'),
        ('idle', '闲置'),
        ('maintenance', '维护中'),
        ('retired', '已报废'),
        ('lent', '已借出'),
    )

    # 基本信息
    name = models.CharField('资产名称', max_length=200)
    asset_type = models.CharField('资产类型', max_length=50, choices=ASSET_TYPE_CHOICES)
    brand = models.CharField('品牌', max_length=100, blank=True)
    model = models.CharField('型号', max_length=100, blank=True)
    serial_number = models.CharField('序列号', max_length=100, unique=True, blank=True)

    # 网络信息
    ip_address = models.GenericIPAddressField('IP地址', blank=True, null=True)
    mac_address = models.CharField('MAC地址', max_length=50, blank=True)

    # 配置信息
    configuration = models.TextField('配置信息', blank=True, help_text='如：CPU、内存、硬盘等配置')
    version = models.CharField('软件版本', max_length=100, blank=True)
    license_expiry = models.DateField('许可到期时间', blank=True, null=True)

    # 责任人信息
    borrower = models.CharField('借货人', max_length=100, blank=True)
    responsible_person = models.CharField('负责人', max_length=100)
    department = models.CharField('所属部门', max_length=100, default='交付部')

    # 状态和位置
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='in_use')
    location = models.CharField('存放位置', max_length=200, blank=True)

    # 其他信息
    purchase_date = models.DateField('购买日期', blank=True, null=True)
    purchase_price = models.DecimalField('购买价格', max_digits=10, decimal_places=2, blank=True, null=True)
    warranty_expiry = models.DateField('保修到期', blank=True, null=True)
    notes = models.TextField('备注', blank=True)

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, verbose_name='创建人', related_name='created_assets')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '资产'
        verbose_name_plural = '资产管理'
        indexes = [
            models.Index(fields=['asset_type', 'status']),
            models.Index(fields=['responsible_person']),
            models.Index(fields=['serial_number']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_asset_type_display()})"

    def get_status_color(self):
        """获取状态对应的颜色"""
        color_map = {
            'in_use': 'success',
            'idle': 'secondary',
            'maintenance': 'warning',
            'retired': 'danger',
            'lent': 'info',
        }
        return color_map.get(self.status, 'secondary')


class AssetCredential(models.Model):
    """资产登录凭据模型（支持多组用户名密码）"""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='credentials', verbose_name='所属资产')
    credential_type = models.CharField('凭据类型', max_length=50,
                                       choices=[
                                           ('admin', '管理员'),
                                           ('user', '普通用户'),
                                           ('security_admin', '安全管理员'),
                                           ('sys_admin', '系统管理员'),
                                           ('root', 'Root'),
                                           ('other', '其他'),
                                       ])
    username = models.CharField('用户名', max_length=100)
    password = models.CharField('密码', max_length=200)  # 建议实际使用时加密存储
    description = models.CharField('描述', max_length=200, blank=True,
                                   help_text='如：默认管理员账户、SSH登录等')

    class Meta:
        verbose_name = '资产凭据'
        verbose_name_plural = '资产凭据管理'
        unique_together = ['asset', 'credential_type', 'username']

    def __str__(self):
        return f"{self.asset.name} - {self.get_credential_type_display()} ({self.username})"


class AssetPhoto(models.Model):
    """资产照片"""

    asset = models.ForeignKey(Asset, on_delete=models.CASCADE, related_name='photos', verbose_name='所属资产')
    photo = models.ImageField('照片', upload_to='asset_photos/%Y/%m/%d/')
    description = models.CharField('描述', max_length=200, blank=True)
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']
        verbose_name = '资产照片'
        verbose_name_plural = '资产照片'

    def __str__(self):
        return f"{self.asset.name} 的照片"


class Project(models.Model):
    """部署项目"""
    STATUS_CHOICES = (
        ('active', '活跃'),
        ('inactive', '停用'),
        ('maintenance', '维护中'),
    )
    
    name = models.CharField('项目名称', max_length=100)
    code = models.CharField('项目代号', max_length=50, unique=True)
    description = models.TextField('项目描述', blank=True)
    
    # 关联虚拟机（多对多）
    virtual_machines = models.ManyToManyField('VirtualMachine', through='ProjectVMRelation', 
                                              verbose_name='关联虚拟机')
    
    # 部署配置路径
    cpp_install_path = models.CharField('C++程序安装路径', max_length=200, 
                                        default='/usr/local/PCMS/PCMS')
    java_install_path = models.CharField('Java程序安装路径', max_length=200,
                                        default='/usr/local/PCMS/tomcat')
    backup_path = models.CharField('更新备份文件路径', max_length=200, 
                                  default='/opt/upbak')
    java_port = models.IntegerField('Java端口', default=80)
    cpp_port = models.IntegerField('C++端口', default=8500)
    ssh_timeout = models.IntegerField('SSH超时时间(秒)', default=30)
    health_check_timeout = models.IntegerField('健康检查超时时间(秒)', default=30)
    
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                   null=True, verbose_name='创建人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '部署项目'
        verbose_name_plural = '部署项目管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    def get_online_vms(self):
        """获取在线的虚拟机"""
        return self.virtual_machines.filter(status='running')


class ProjectVMRelation(models.Model):
    """项目与虚拟机关联表（存储项目中覆盖的IP）"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='项目')
    virtual_machine = models.ForeignKey('VirtualMachine', on_delete=models.CASCADE, verbose_name='虚拟机')
    custom_ip = models.CharField('覆盖IP地址', max_length=50, blank=True, 
                                 help_text='如果为空则使用虚拟机IP，否则使用此IP')
    ssh_username = models.CharField('SSH用户名', max_length=50, default='root')
    ssh_password = models.CharField('SSH密码', max_length=200, blank=True)
    ssh_key_path = models.CharField('SSH密钥路径', max_length=200, blank=True)
    ssh_port = models.IntegerField('SSH端口', default=22)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '项目虚拟机关联'
        verbose_name_plural = '项目虚拟机关联管理'
        unique_together = ['project', 'virtual_machine']
    
    def __str__(self):
        return f"{self.project.name} - {self.virtual_machine.name}"
    
    def get_ip(self):
        """获取IP地址（优先使用覆盖IP）"""
        return self.custom_ip or self.virtual_machine.ip_address
    
    def save(self, *args, **kwargs):
        # 保存时同步IP到虚拟机表（如果有覆盖IP）
        if self.custom_ip and self.custom_ip != self.virtual_machine.ip_address:
            self.virtual_machine.ip_address = self.custom_ip
            self.virtual_machine.save(update_fields=['ip_address'])
        super().save(*args, **kwargs)



class DeploymentServer(models.Model):
    """部署服务器"""
    OS_CHOICES = (
        ('centos', 'CentOS'),
        ('ubuntu', 'Ubuntu'),
        ('kylin_v10', '麒麟V10'),
        ('windows', 'Windows Server'),
        ('other', '其他'),
    )
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, 
                                related_name='servers', verbose_name='所属项目')
    name = models.CharField('服务器名称', max_length=100)
    hostname = models.CharField('主机名', max_length=100)
    ip_address = models.CharField('IP地址', max_length=50)
    ssh_port = models.IntegerField('SSH端口', default=22)
    ssh_username = models.CharField('SSH用户名', max_length=50)
    ssh_password = models.CharField('SSH密码', max_length=200, blank=True)
    ssh_key_path = models.CharField('SSH密钥路径', max_length=200, blank=True)
    os_type = models.CharField('操作系统', max_length=20, choices=OS_CHOICES, default='centos')
    
    # 部署路径配置
    cpp_install_path = models.CharField('C++程序安装路径', max_length=200, 
                                        default='/usr/local/PCMS/PCMS')
    java_install_path = models.CharField('Java程序安装路径', max_length=200,
                                        default='/usr/local/PCMS/tomcat')
    backup_path = models.CharField('更新备份路径', max_length=200, default='/opt/upbak')
    
    # 端口配置
    java_port = models.IntegerField('Java端口', default=80)
    cpp_port = models.IntegerField('C++端口', default=8500)
    
    # 状态信息
    is_online = models.BooleanField('在线状态', default=True)
    last_check_time = models.DateTimeField('最后检查时间', null=True, blank=True)
    description = models.TextField('描述', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '部署服务器'
        verbose_name_plural = '部署服务器管理'
        ordering = ['project', 'name']
        unique_together = ['project', 'ip_address']
    
    def __str__(self):
        return f"{self.name} ({self.ip_address})"
    
    def get_status_color(self):
        """获取状态颜色"""
        return 'success' if self.is_online else 'danger'


class DeploymentPackage(models.Model):
    """部署包"""
    PACKAGE_TYPE_CHOICES = (
        ('java_full', 'Java全量包(pcms.war)'),
        ('java_incremental', 'Java增量包(pcms.zip)'),
        ('cpp_program', 'C++程序(pcms)'),
        ('h5_package', 'H5包(confApp.zip)'),
        ('java_log_full', 'Java日志全量包(pcmsLog.war)'),
        ('java_log_incremental', 'Java日志增量包(pcmsLog.zip)'),
    )
    
    name = models.CharField('包名称', max_length=200)
    package_type = models.CharField('包类型', max_length=30, choices=PACKAGE_TYPE_CHOICES)
    version = models.CharField('版本号', max_length=50)
    file_path = models.CharField('文件路径', max_length=500)
    file_size = models.BigIntegerField('文件大小(B)', default=0)
    md5_hash = models.CharField('MD5校验值', max_length=32, blank=True)
    description = models.TextField('描述', blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, verbose_name='上传人')
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)
    is_active = models.BooleanField('是否有效', default=True)
    original_filename = models.CharField(max_length=500, verbose_name='原始文件名', blank=True)   
 
    class Meta:
        verbose_name = '部署包'
        verbose_name_plural = '部署包管理'
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.name} ({self.version})"


class DeploymentTask(models.Model):
    """部署任务"""
    STATUS_CHOICES = (
        ('pending', '等待中'),
        ('uploading', '上传文件中'),
        ('uploaded', '文件上传完成'),
        ('deploying', '部署中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    )
    
    task_id = models.CharField('任务ID', max_length=50, unique=True, editable=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, verbose_name='所属项目')
    package = models.ForeignKey(DeploymentPackage, on_delete=models.CASCADE, 
                               verbose_name='部署包', null=True, blank=True)  # 添加 null=True, blank=True
    name = models.CharField('任务名称', max_length=200)
    description = models.TextField('任务描述', blank=True)
    
    # 任务状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    progress = models.IntegerField('进度(%)', default=0)
    log_content = models.TextField('日志内容', blank=True)
    
    # 执行信息
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                  verbose_name='创建人')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    
    class Meta:
        verbose_name = '部署任务'
        verbose_name_plural = '部署任务管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.task_id} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.task_id:
            import uuid
            self.task_id = f"DEPLOY-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class TaskPackageRelation(models.Model):
    """任务与包关联表"""
    task = models.ForeignKey(DeploymentTask, on_delete=models.CASCADE)
    package = models.ForeignKey(DeploymentPackage, on_delete=models.CASCADE)
    upload_status = models.CharField('上传状态', max_length=20, default='pending')
    upload_progress = models.IntegerField('上传进度', default=0)
    uploaded_at = models.DateTimeField('上传完成时间', null=True, blank=True)
    
    class Meta:
        unique_together = ['task', 'package']


class TaskServerRelation(models.Model):
    """任务与服务器关联表"""
    task = models.ForeignKey(DeploymentTask, on_delete=models.CASCADE)
    server = models.ForeignKey(DeploymentServer, on_delete=models.CASCADE)
    deploy_status = models.CharField('部署状态', max_length=20, default='pending')
    deploy_progress = models.IntegerField('部署进度', default=0)
    deploy_log = models.TextField('部署日志', blank=True)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    
    class Meta:
        unique_together = ['task', 'server']


class DeploymentScript(models.Model):
    """部署脚本"""
    project = models.OneToOneField(Project, on_delete=models.CASCADE,
                                   related_name='deployment_script', verbose_name='所属项目')
    content = models.TextField('脚本内容')
    version = models.CharField('版本号', max_length=20, default='1.0')
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '部署脚本'
        verbose_name_plural = '部署脚本管理'

    def __str__(self):
        return f"{self.project.name} 的部署脚本"

    def save(self, *args, **kwargs):
        # 🔥 统一换行符：Windows CRLF 和旧 Mac CR 全部转为 Unix LF
        if self.content:
            self.content = self.content.replace('\r\n', '\n').replace('\r', '\n')
        super().save(*args, **kwargs)


class DeploymentHistory(models.Model):
    """部署历史记录"""
    task = models.ForeignKey(DeploymentTask, on_delete=models.CASCADE, verbose_name='关联任务')
    project_vm = models.ForeignKey(ProjectVMRelation, on_delete=models.CASCADE, 
                                  verbose_name='项目虚拟机', null=True, blank=True)  # 添加 null=True, blank=True
    
    # 部署信息
    package_version = models.CharField('包版本', max_length=50, default='')  # 添加默认值
    script_content = models.TextField('执行脚本内容', blank=True)
    
    # 执行结果
    status = models.CharField('部署状态', max_length=20, default='pending')  # 添加默认值
    message = models.TextField('结果信息', blank=True)
    java_service_healthy = models.BooleanField('Java服务正常', default=False)
    cpp_service_healthy = models.BooleanField('C++服务正常', default=False)
    error_message = models.TextField('错误信息', blank=True)
    
    # 时间信息
    started_at = models.DateTimeField('开始时间', null=True, blank=True)  # 允许为空
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)  # 允许为空
    duration = models.IntegerField('持续时间(秒)', default=0)  # 添加默认值
    
    class Meta:
        verbose_name = '部署历史'
        verbose_name_plural = '部署历史记录'
        ordering = ['-completed_at']
    
    def __str__(self):
        if self.project_vm:
            return f"{self.task.task_id} - {self.project_vm.virtual_machine.name}"
        else:
            return f"{self.task.task_id} - 无关联虚拟机"
    
    @property
    def is_success(self):
        """是否成功"""
        return self.status == 'success'
