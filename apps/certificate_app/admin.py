# -*- coding: utf-8 -*-
"""
certificate_app Django Admin 配置

证书管理模块的 Admin 配置
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Certificate


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """证书模型的后台管理配置"""

    # 列表页显示字段
    list_display = [
        'certificate_no', 'student_link', 'training_class_link',
        'training_type', 'status_badge', 'validity_period',
        'is_valid_badge', 'issued_at', 'is_deleted'
    ]

    # 搜索框
    search_fields = [
        'certificate_no', 'student__name', 'student__id_card',
        'training_class__class_no', 'issued_by__name'
    ]

    # 右侧过滤栏
    list_filter = [
        'status', 'training_type', 'training_class__training_type',
        'is_deleted', 'issued_at', 'validity_end'
    ]

    # 默认排序
    ordering = ['-issued_at']

    # 每页数量
    list_per_page = 20

    # 日期层级导航
    date_hierarchy = 'issued_at'

    # 字段分组展示
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'certificate_no', 'student', 'training_class', 'training_type')
        }),
        ('证书信息', {
            'fields': ('issued_at', 'validity_start', 'validity_end', 'status')
        }),
        ('证书状态', {
            'fields': ('revoke_reason', 'issued_by', 'remark')
        }),
        ('审计信息', {
            'fields': ('idem_key', 'is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # 只读字段
    readonly_fields = ['id', 'issued_at', 'created_at', 'updated_at', 'idem_key']

    # 列表页每行操作
    list_display_links = ['certificate_no']

    # 批量操作
    actions = ['soft_delete', 'restore', 'revoke_certificates', 'mark_as_lost']

    def get_queryset(self, request):
        """优化查询，减少 N+1 问题"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'student',
            'training_class',
            'training_class__training_type',
            'training_type',
            'issued_by'
        )

    # -------------------
    # 自定义显示方法
    # -------------------

    @admin.display(description='学员', ordering='student__name')
    def student_link(self, obj):
        """学员链接跳转"""
        return format_html(
            '<a href="/admin/student_app/student/{}/change/">{}</a>',
            obj.student.id,
            obj.student.name
        )

    @admin.display(description='培训班', ordering='training_class__class_no')
    def training_class_link(self, obj):
        """班级链接跳转"""
        return format_html(
            '<a href="/admin/training_app/trainingclass/{}/change/">{}</a>',
            obj.training_class.id,
            obj.training_class.class_no
        )

    @admin.display(description='证书状态', ordering='status')
    def status_badge(self, obj):
        """证书状态标签展示"""
        color_map = {
            'issued': '#27ae60',   # 绿色-已发放
            'revoked': '#e74c3c',  # 红色-已撤销
            'lost': '#f39c12',     # 橙色-已挂失
        }
        color = color_map.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.display(description='有效期', ordering='validity_end')
    def validity_period(self, obj):
        """有效期显示"""
        if obj.is_expired:
            return format_html(
                '<span style="color: #e74c3c;">已过期</span> '
                '({} ~ {})',
                obj.validity_start, obj.validity_end
            )
        days = obj.days_to_expire
        if days <= 90:
            color = '#f39c12'
        else:
            color = '#27ae60'
        return format_html(
            '<span style="color: {};">{} 天</span> '
            '({} ~ {})',
            color, days, obj.validity_start, obj.validity_end
        )

    @admin.display(description='有效', boolean=True)
    def is_valid_badge(self, obj):
        """是否有效"""
        return obj.is_valid

    # -------------------
    # 批量操作方法
    # -------------------

    @admin.action(description='软删除选中证书')
    def soft_delete(self, request, queryset):
        """批量软删除证书"""
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条证书记录')

    @admin.action(description='恢复选中证书')
    def restore(self, request, queryset):
        """批量恢复已删除的证书"""
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条证书记录')

    @admin.action(description='撤销选中学员证书')
    def revoke_certificates(self, request, queryset):
        """批量撤销证书"""
        count = queryset.update(status='revoked')
        self.message_user(request, f'已撤销 {count} 条证书')

    @admin.action(description='挂失选中学员证书')
    def mark_as_lost(self, request, queryset):
        """批量挂失证书"""
        count = queryset.update(status='lost')
        self.message_user(request, f'已挂失 {count} 条证书')

    # -------------------
    # 权限控制
    # -------------------

    def get_queryset(self, request):
        """非超级用户只能看到未删除的记录"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs
