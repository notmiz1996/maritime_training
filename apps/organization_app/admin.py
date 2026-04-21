"""
组织架构模块 - Admin 后台管理配置

参考：后端开发与验收手册 - Django Admin 规范
"""

from django.contrib import admin
from .models import Organization, Personnel, Position, PersonnelPosition


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """
    Organization 模型的后台管理配置

    功能：
    - 列表页显示关键字段
    - 搜索支持 name
    - 层级展示（通过 path）
    - 软删除过滤
    """

    # ========== 列表页配置 ==========
    # 列表显示的字段
    list_display = [
        'id',
        'name',
        'org_type',
        'level',
        'parent',
        'path',
        'is_deleted',
        'created_at',
    ]

    # 可搜索的字段
    search_fields = ['name', 'path']

    # 过滤器
    list_filter = [
        'org_type',  # 按组织类型过滤
        'level',  # 按层级过滤
        'is_deleted',  # 按是否删除过滤
    ]

    # 排序
    ordering = ['path']

    # 分页
    list_per_page = 50

    # ========== 详情页配置 ==========
    # 详情页显示的字段分组
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'name', 'org_type')
        }),
        ('层级结构', {
            'fields': ('parent', 'level', 'path'),
            'description': '层级结构由系统自动计算，修改上级组织时会自动更新'
        }),
        ('审计信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',),  # 可折叠
        }),
    )

    # ========== 只读字段 ==========
    # 这些字段不允许在后台直接修改
    readonly_fields = ['id', 'level', 'path', 'created_at', 'updated_at']

    # ========== 动作配置 ==========
    # 批量操作
    actions = ['soft_delete', 'restore']

    @admin.action(description='软删除选中的组织')
    def soft_delete(self, request, queryset):
        """批量软删除"""
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条记录')

    @admin.action(description='恢复选中的组织')
    def restore(self, request, queryset):
        """批量恢复"""
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条记录')

    # ========== 查询优化 ==========
    def get_queryset(self, request):
        """默认只显示未删除的记录"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # 非超级管理员只能看到未删除的记录
            qs = qs.filter(is_deleted=False)
        return qs

@admin.register(Personnel)
class PersonnelAdmin(admin.ModelAdmin):
    """人员模型的后台管理配置"""

    list_display = [
        'id', 'name', 'id_card_masked', 'phone',
        'organization', 'user_link', 'is_deleted', 'created_at'
    ]
    search_fields = ['name', 'id_card', 'phone', 'user__username']
    list_filter = ['organization', 'is_deleted', 'created_at']
    ordering = ['-created_at']
    list_per_page = 50

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'name', 'id_card', 'phone')
        }),
        ('组织信息', {
            'fields': ('organization', 'user')
        }),
        ('审计信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'created_at', 'updated_at']

    actions = ['soft_delete', 'restore']

    @admin.display(description='身份证号', ordering='id_card')
    def id_card_masked(self, obj):
        """脱敏展示：前4后4"""
        if len(obj.id_card) >= 8:
            return f"{obj.id_card[:4]}****{obj.id_card[-4:]}"
        return obj.id_card

    @admin.display(description='关联用户')
    def user_link(self, obj):
        if obj.user:
            return format_html(
                '<a href="/admin/auth/user/{}/change/">{}</a>',
                obj.user.id, obj.user.username
            )
        return '-'
    user_link.short_description = '关联用户'

    @admin.action(description='软删除选中人员')
    def soft_delete(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条记录')

    @admin.action(description='恢复选中人员')
    def restore(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条记录')

    def get_queryset(self, request):
        """默认过滤已删除记录"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    """职务模型的后台管理配置"""

    list_display = ['id', 'name', 'code', 'organization', 'is_concurrentable', 'is_deleted', 'created_at']
    search_fields = ['name', 'code', 'organization__name']
    list_filter = ['organization', 'is_concurrentable', 'is_deleted']
    ordering = ['organization__path', 'code']
    list_per_page = 50

    fieldsets = (
        ('基本信息', {'fields': ('id', 'name', 'code', 'organization')}),
        ('权限配置', {'fields': ('permissions', 'is_concurrentable')}),
        ('审计信息', {'fields': ('is_deleted', 'created_at', 'updated_at'), 'classes': ('collapse',)}),
    )

    readonly_fields = ['id', 'created_at', 'updated_at']

    actions = ['soft_delete', 'restore']

    @admin.action(description='软删除选中职务')
    def soft_delete(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条记录')

    @admin.action(description='恢复选中职务')
    def restore(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条记录')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs


@admin.register(PersonnelPosition)
class PersonnelPositionAdmin(admin.ModelAdmin):
    """人员职务关联模型的后台管理配置"""

    list_display = ['id', 'personnel_link', 'position_link', 'is_primary', 'is_active', 'created_at']
    search_fields = ['personnel__name', 'position__name', 'position__code']
    list_filter = ['is_primary', 'is_active', 'position__organization']
    ordering = ['-is_primary', '-created_at']
    list_per_page = 50

    fieldsets = (
        ('关联信息', {'fields': ('id', 'personnel', 'position', 'is_primary', 'is_active')}),
        ('审计信息', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )

    readonly_fields = ['id', 'created_at']

    @admin.display(description='人员', ordering='personnel__name')
    def personnel_link(self, obj):
        return format_html(
            '<a href="/admin/organization_app/personnel/{}/change/">{}</a>',
            obj.personnel.id, obj.personnel.name
        )

    @admin.display(description='职务', ordering='position__name')
    def position_link(self, obj):
        return format_html(
            '<a href="/admin/organization_app/position/{}/change/">{}</a>',
            obj.position.id, obj.position.name
        )
