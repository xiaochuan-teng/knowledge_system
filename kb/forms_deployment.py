# kb/forms_deployment.py
from django import forms
from django.forms import ModelForm, inlineformset_factory
from .models import Project, ProjectVMRelation, DeploymentPackage, DeploymentScript, DeploymentTask, DeploymentServer

class ProjectForm(ModelForm):
    """项目表单"""
    class Meta:
        model = Project
        fields = [
            'name', 'code', 'description', 'status',
            'cpp_install_path', 'java_install_path', 'backup_path',
            'java_port', 'cpp_port', 'ssh_timeout', 'health_check_timeout'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'cpp_install_path': forms.TextInput(attrs={'class': 'form-control'}),
            'java_install_path': forms.TextInput(attrs={'class': 'form-control'}),
            'backup_path': forms.TextInput(attrs={'class': 'form-control'}),
            'java_port': forms.NumberInput(attrs={'class': 'form-control'}),
            'cpp_port': forms.NumberInput(attrs={'class': 'form-control'}),
            'ssh_timeout': forms.NumberInput(attrs={'class': 'form-control'}),
            'health_check_timeout': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': '项目名称',
            'code': '项目代号',
            'description': '项目描述',
            'status': '状态',
            'cpp_install_path': 'C++程序安装路径',
            'java_install_path': 'Java程序安装路径',
            'backup_path': '更新备份文件路径',
            'java_port': 'Java端口',
            'cpp_port': 'C++端口',
            'ssh_timeout': 'SSH超时时间(秒)',
            'health_check_timeout': '健康检查超时时间(秒)',
        }


class ProjectVMForm(forms.ModelForm):
    """项目虚拟机表单 - 已修改为搜索模式"""
    vm_search = forms.CharField(
        required=False,
        label='搜索虚拟机',
        widget=forms.TextInput(attrs={
            'class': 'form-control vm-search-input',
            'placeholder': '输入虚拟机名称或IP搜索...',
            'autocomplete': 'off'
        })
    )
    
    class Meta:
        model = ProjectVMRelation
        fields = ['virtual_machine', 'custom_ip', 'ssh_username', 'ssh_password', 
                 'ssh_key_path', 'ssh_port']
        widgets = {
            'virtual_machine': forms.HiddenInput(attrs={'class': 'vm-id-input'}),
            'custom_ip': forms.TextInput(attrs={'class': 'form-control ip-input'}),
            'ssh_username': forms.TextInput(attrs={'class': 'form-control', 'value': 'root'}),
            'ssh_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'render_value': True,
                'autocomplete': 'new-password'
            }),
            'ssh_key_path': forms.TextInput(attrs={'class': 'form-control'}),
            'ssh_port': forms.NumberInput(attrs={'class': 'form-control', 'value': 22}),
        }
        labels = {
            'custom_ip': '覆盖IP地址（为空则使用虚拟机IP）',
            'ssh_username': 'SSH用户名',
            'ssh_password': 'SSH密码',
            'ssh_key_path': 'SSH密钥路径',
            'ssh_port': 'SSH端口',
        }

# 修改 ProjectVMFormSet 的配置
ProjectVMFormSet = inlineformset_factory(
    Project,
    ProjectVMRelation,
    form=ProjectVMForm,
    extra=0,  # 改为0，我们将手动管理表单数量
    can_delete=True,
    can_delete_extra=True,
    min_num=1,
    validate_min=True,
)


class DeploymentPackageForm(ModelForm):
    """部署包表单"""
    class Meta:
        model = DeploymentPackage
        fields = ['name', 'package_type', 'version', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'package_type': forms.Select(attrs={'class': 'form-select'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'name': '包名称',
            'package_type': '包类型',
            'version': '版本号',
            'description': '描述',
        }


class PackageUploadForm(forms.Form):
    """包上传表单（快速部署）"""
    project = forms.ModelChoiceField(
        label='所属项目',
        queryset=Project.objects.filter(status='active'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    package_type = forms.ChoiceField(
        label='包类型',
        choices=(
            ('', '请选择包类型'),
            ('java_full', 'Java全量包(pcms.war)'),
            ('java_incremental', 'Java增量包(pcms.zip)'),
            ('cpp_program', 'C++程序(pcms)'),
            ('h5_package', 'H5包(confApp.zip)'),
            ('java_log_full', 'Java日志全量包(pcmsLog.war)'),
            ('java_log_incremental', 'Java日志增量包(pcmsLog.zip)'),
        ),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    version = forms.CharField(
        label='版本号',
        max_length=50,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    description = forms.CharField(
        label='描述',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
    file = forms.FileField(
        label='选择文件',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )


class DeploymentScriptForm(ModelForm):
    """部署脚本表单"""
    class Meta:
        model = DeploymentScript
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 25,
                'style': 'font-family: monospace; font-size: 12px;',
                'spellcheck': 'false'
            }),
        }
        labels = {
            'content': '脚本内容',
        }


class DeploymentTaskForm(ModelForm):
    """部署任务表单"""
    class Meta:
        model = DeploymentTask
        fields = ['project', 'package', 'name', 'description']
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'package': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'project': '所属项目',
            'package': '部署包',
            'name': '任务名称',
            'description': '任务描述',
        }


class DeploymentServerForm(forms.ModelForm):
    """部署服务器表单"""
    class Meta:
        model = DeploymentServer
        fields = [
            'project', 'name', 'hostname', 'ip_address', 'ssh_port', 
            'ssh_username', 'ssh_password', 'ssh_key_path', 'os_type',
            'cpp_install_path', 'java_install_path', 'backup_path',
            'java_port', 'cpp_port', 'description'
        ]
        widgets = {
            'project': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'hostname': forms.TextInput(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'ssh_port': forms.NumberInput(attrs={'class': 'form-control', 'value': 22}),
            'ssh_username': forms.TextInput(attrs={'class': 'form-control', 'value': 'root'}),
            'ssh_password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'render_value': True,
                'autocomplete': 'new-password'
            }),
            'ssh_key_path': forms.TextInput(attrs={'class': 'form-control'}),
            'os_type': forms.Select(attrs={'class': 'form-select'}),
            'cpp_install_path': forms.TextInput(attrs={'class': 'form-control'}),
            'java_install_path': forms.TextInput(attrs={'class': 'form-control'}),
            'backup_path': forms.TextInput(attrs={'class': 'form-control'}),
            'java_port': forms.NumberInput(attrs={'class': 'form-control', 'value': 80}),
            'cpp_port': forms.NumberInput(attrs={'class': 'form-control', 'value': 8500}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
        labels = {
            'project': '所属项目',
            'name': '服务器名称',
            'hostname': '主机名',
            'ip_address': 'IP地址',
            'ssh_port': 'SSH端口',
            'ssh_username': 'SSH用户名',
            'ssh_password': 'SSH密码',
            'ssh_key_path': 'SSH密钥路径',
            'os_type': '操作系统',
            'cpp_install_path': 'C++程序安装路径',
            'java_install_path': 'Java程序安装路径',
            'backup_path': '更新备份路径',
            'java_port': 'Java端口',
            'cpp_port': 'C++端口',
            'description': '描述',
        }
