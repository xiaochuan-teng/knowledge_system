# kb/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Article, Attachment, Comment
from django.utils.html import format_html
from .models import HostMachine, VirtualMachine
from django.contrib import admin
from .models import Asset, AssetCredential, AssetPhoto


# ============ 用户管理 ============
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'role', 'department', 'is_staff', 'is_active']
    list_filter = ['role', 'department', 'is_staff', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('扩展信息', {'fields': ('role', 'department')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('扩展信息', {'fields': ('role', 'department')}),
    )


# ============ 内联类定义 ============
class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 1


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1
    readonly_fields = ['created_at']


# ============ 文章管理 ============
@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'article_type', 'is_resolved', 'views', 'created_at']
    list_filter = ['article_type', 'is_resolved', 'created_at']
    search_fields = ['title', 'content', 'tags']
    readonly_fields = ['views', 'created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'content', 'author')
        }),
        ('分类信息', {
            'fields': ('article_type', 'product_version', 'project_name', 'tags')
        }),
        ('状态信息', {
            'fields': ('is_resolved', 'views', 'created_at', 'updated_at')
        }),
    )
    inlines = [AttachmentInline, CommentInline]

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


# ============ 附件管理 ============
@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'article', 'file_type', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['file_name', 'article__title']
    readonly_fields = ['uploaded_at']


# ============ 评论管理 ============
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'article', 'content_preview', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username', 'article__title']
    readonly_fields = ['created_at']

    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_preview.short_description = '评论内容预览'

@admin.register(HostMachine)
class HostMachineAdmin(admin.ModelAdmin):
    list_display = ['name', 'ip_address', 'status', 'last_check_time', 'location', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['name', 'ip_address', 'location']
    readonly_fields = ['last_check_time', 'created_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'ip_address', 'location')
        }),
        ('连接信息', {
            'fields': ('username', 'password', 'port')
        }),
        ('状态信息', {
            'fields': ('status', 'last_check_time', 'description')
        }),
        ('时间信息', {
            'fields': ('created_at',)
        }),
    )

@admin.register(VirtualMachine)
class VirtualMachineAdmin(admin.ModelAdmin):
    list_display = ['name', 'ip_address', 'host_machine', 'owner', 'os', 'status']
    list_filter = ['os', 'status', 'created_at']
    search_fields = ['name', 'ip_address', 'owner__username']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'ip_address', 'host_machine', 'owner')
        }),
        ('硬件配置', {
            'fields': ('cpu', 'memory', 'disk')
        }),
        ('系统信息', {
            'fields': ('os', 'os_version', 'status')
        }),
        ('其他信息', {
            'fields': ('purpose', 'notes', 'created_at', 'updated_at')
        }),
    )
# ============ 注册用户模型 ============
admin.site.register(CustomUser, CustomUserAdmin)

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ['name', 'asset_type', 'ip_address', 'responsible_person', 'status', 'created_at']
    list_filter = ['asset_type', 'status', 'department']
    search_fields = ['name', 'serial_number', 'ip_address', 'responsible_person']
    list_per_page = 20

@admin.register(AssetCredential)
class AssetCredentialAdmin(admin.ModelAdmin):
    list_display = ['asset', 'credential_type', 'username', 'description']
    list_filter = ['credential_type']

@admin.register(AssetPhoto)
class AssetPhotoAdmin(admin.ModelAdmin):
    list_display = ['asset', 'description', 'uploaded_at']
