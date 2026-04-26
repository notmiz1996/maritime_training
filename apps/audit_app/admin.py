# -*- coding: utf-8 -*-
"""
audit_app Django Admin 配置

包含：AuditLog 的 Admin 配置
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """审计日志模型的后台管理配置"""

    list_display = [
        'id', 'operator_link', 'action_badge',
        'process_instance_link', 'ip_address', 'created_at'
    ]
    search_fields = [
        'operator__name', 'action',
        'comment', 'ip_address'
    ]
    list_filter = [
        'action', 'operator',
        'created_at'
    ]
    ordering = ['-created_at']
    list_per_page = 50
    date_hierarchy = 'created_at'

    fieldsets = (
        ('操作信息', {
            'fields': ('id', 'operator', 'action')
        }),
        ('流程关联', {
            'fields': ('process_instance',)
        }),
        ('状态变更', {
            'fields': ('before_state', 'after_state'),
            'classes': ('collapse',)
        }),
        ('请求上下文', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('备注', {
            'fields': ('comment',)
        }),
        ('审计信息', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'created_at']
    list_display_links = ['id']

    # 禁止新增/修改/删除（审计日志只能系统写入）
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'operator',
            'process_instance'
        )

    @admin.display(description='操作人员', ordering='operator__name')
    def operator_link(self, obj):
        if obj.operator:
            return format_html(
                '<a href="/admin/organization_app/personnel/{}/change/">{}</a>',
                obj.operator.id,
                obj.operator.name
            )
        return '系统'

    @admin.display(description='操作动作', ordering='action')
    def action_badge(self, obj):
        color_map = {
            'create': '#27ae60',
            'update': '#3498db',
            'delete': '#e74c3c',
            'soft_delete': '#e67e22',
            'restore': '#9b59b6',
            'status_change': '#f39c12',
            'approve': '#1abc9c',
            'reject': '#e74c3c',
            'checkin': '#3498db',
            'certificate_issued': '#27ae60',
            'certificate_revoked': '#e74c3c',
            'login': '#95a5a6',
            'logout': '#95a5a6',
        }
        color = color_map.get(obj.action, '#7f8c8d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.action
        )

    @admin.display(description='流程实例', ordering='process_instance')
    def process_instance_link(self, obj):
        if obj.process_instance:
            return format_html(
                '<a href="/admin/workflow_app/processinstance/{}/change/">{}</a>',
                obj.process_instance.id,
                obj.process_instance.process_key
            )
        return '-'
