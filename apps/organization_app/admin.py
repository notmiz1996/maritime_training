"""
组织架构模块 - Admin 后台管理配置

参考：后端开发与验收手册 - Django Admin 规范
"""

from django.contrib import admin
from .models import Organization


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