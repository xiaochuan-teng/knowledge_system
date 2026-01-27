from django import forms
from django.forms import ModelForm, inlineformset_factory
#from ckeditor.widgets import CKEditorWidget
from .models import Article, Comment, HostMachine, VirtualMachine
from django_ckeditor_5.widgets import CKEditor5Widget
from .models import Asset, AssetCredential, AssetPhoto


class ArticleForm(ModelForm):
    # 使用CKEditorWidget替换默认的文本区域
    # content = forms.CharField(widget=CKEditor5Widget(), label='内容')

    # 修复：使用 MultipleFileInput 替代 ClearableFileInput
    attachments = forms.FileField(
        widget=forms.ClearableFileInput(),  # 去掉 multiple=True
        required=False,
        label='上传附件（可多选）'
    )

    class Meta:
        model = Article
        fields = [
            'title', 'content', 'article_type',
            'product_version', 'project_name', 'tags', 'is_resolved'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '请输入文章标题'
            }),
            'content': CKEditor5Widget(
                config_name='default',
                attrs={'class': 'django_ckeditor_5'
            }),
            'article_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'product_version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '如：V3.0.1'
            }),
            'project_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '定制项目名称'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '用逗号分隔多个标签，如：网络,故障,紧急'
            }),
            'is_resolved': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'title': '标题',
            'content': '内容',
            'article_type': '问题类型',
            'product_version': '产品版本',
            'project_name': '项目名称',
            'tags': '标签',
            'is_resolved': '问题是否已解决',
        }
        help_texts = {
            'tags': '多个标签用逗号分隔',
            'product_version': '如：V3.0.1, V2.5.2',
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '请输入您的评论...',
                'style': 'resize: vertical;'
            }),
        }
        labels = {
            'content': '评论内容',
        }


class VmForm(ModelForm):
    class Meta:
        model = VirtualMachine
        fields = [
            'name', 'ip_address', 'host_machine', 'owner',
            'cpu', 'memory', 'disk', 'os', 'os_version',
            'status', 'purpose', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'host_machine': forms.Select(attrs={'class': 'form-control'}),
            'owner': forms.Select(attrs={'class': 'form-control'}),
            'cpu': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如：4核'}),
            'memory': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如：8GB'}),
            'disk': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如：100GB'}),
            'os': forms.Select(attrs={'class': 'form-control'}),
            'os_version': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '如：CentOS 7.9'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
        labels = {
            'name': '虚拟机名称',
            'ip_address': 'IP地址',
            'host_machine': '所属宿主机',
            'owner': '责任人',
            'cpu': 'CPU配置',
            'memory': '内存配置',
            'disk': '磁盘配置',
            'os': '操作系统',
            'os_version': '系统版本',
            'status': '状态',
            'purpose': '用途描述',
            'notes': '备注',
        }


class AssetForm(forms.ModelForm):
    class Meta:
        model = Asset
        # 从字段列表中移除 department
        fields = [
            'name', 'asset_type', 'brand', 'model', 'serial_number',
            'ip_address', 'mac_address', 'configuration', 'version',
            'license_expiry', 'borrower', 'responsible_person',
            'status', 'location', 'purchase_date', 'purchase_price',
            'warranty_expiry', 'notes'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'asset_type': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'responsible_person': forms.TextInput(attrs={'class': 'form-control'}),
            'ip_address': forms.TextInput(attrs={'class': 'form-control'}),
            'mac_address': forms.TextInput(attrs={'class': 'form-control'}),
            'version': forms.TextInput(attrs={'class': 'form-control'}),
            'license_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'borrower': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'configuration': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'purchase_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control'}),
            'warranty_expiry': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 为必填字段添加样式
        for field_name, field in self.fields.items():
            if field.required:
                field.label = f"{field.label} *"

class AssetCredentialForm(forms.ModelForm):
    """资产凭据表单 - 添加 Bootstrap 样式"""
    class Meta:
        model = AssetCredential
        fields = ['credential_type', 'username', 'password', 'description']
        widgets = {
            'credential_type': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': '选择凭据类型'
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '用户名'
            }),
            'password': forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': '密码',
                'render_value': True  # 编辑时显示已保存的值
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '描述（可选）'
            }),
        }

class AssetPhotoForm(forms.ModelForm):
    """资产照片表单 - 添加 Bootstrap 样式"""
    class Meta:
        model = AssetPhoto
        fields = ['photo', 'description']
        widgets = {
            'photo': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '照片描述（可选）'
            }),
        }

# 创建内联表单集 - 使用带样式的表单
AssetCredentialFormSet = inlineformset_factory(
    Asset,
    AssetCredential,
    form=AssetCredentialForm,
    extra=1,  # 默认显示1个空白表单
    can_delete=True,
    can_delete_extra=True,
    min_num=0,  # 允许0个表单
    validate_min=False,
)

AssetPhotoFormSet = inlineformset_factory(
    Asset,
    AssetPhoto,
    form=AssetPhotoForm,
    extra=1,
    can_delete=True,
    can_delete_extra=True,
    min_num=0,
    validate_min=False,
)