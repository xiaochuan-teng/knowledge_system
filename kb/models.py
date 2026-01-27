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
