# -*- coding: utf-8 -*-
"""
workflow_app Django Admin 配置

流程实例和流程任务的 Admin 配置
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import ProcessInstance, ProcessTask


@admin.register(ProcessInstance)
class ProcessInstanceAdmin(admin.ModelAdmin):
    """流程实例模型的后台管理配置"""

    # 列表页显示字段
    list_display = [
        'id', 'process_name', 'process_key', 'status_badge',
        'current_task_name', 'initiator_link', 'duration_display',
        'started_at', 'is_deleted'
    ]

    # 搜索框
    search_fields = [
        'process_name', 'process_key', 'initiator__name',
        'related_object_type', 'related_object_id'
    ]

    # 右侧过滤栏
    list_filter = [
        'status', 'process_key', 'is_deleted', 'started_at'
    ]

    # 默认排序
    ordering = ['-started_at']

    # 每页数量
    list_per_page = 20

    # 日期层级导航
    date_hierarchy = 'started_at'

    # 字段分组展示
    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'process_key', 'process_name', 'bpmn_file')
        }),
        ('流程状态', {
            'fields': ('status', 'current_task_id', 'current_task_name')
        }),
        ('关联信息', {
            'fields': ('initiator', 'related_object_type', 'related_object_id')
        }),
        ('流程变量', {
            'fields': ('variables',),
            'classes': ('collapse',)
        }),
        ('时间记录', {
            'fields': ('started_at', 'completed_at', 'suspended_at')
        }),
        ('审计信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    # 只读字段
    readonly_fields = ['id', 'started_at', 'completed_at', 'suspended_at', 'created_at', 'updated_at']

    # 列表页每行操作
    list_display_links = ['id', 'process_name']

    # 批量操作
    actions = ['soft_delete', 'restore', 'suspend_processes', 'terminate_processes']

    def get_queryset(self, request):
        """优化查询，减少 N+1 问题"""
        qs = super().get_queryset(request)
        return qs.select_related('initiator')

    @admin.display(description='状态', ordering='status')
    def status_badge(self, obj):
        """流程状态标签展示"""
        color_map = {
            'running': '#27ae60',
            'suspended': '#f39c12',
            'completed': '#3498db',
            'terminated': '#e74c3c',
        }
        color = color_map.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.display(description='发起人', ordering='initiator__name')
    def initiator_link(self, obj):
        """发起人链接跳转"""
        if obj.initiator:
            return format_html(
                '<a href="/admin/organization_app/personnel/{}/change/">{}</a>',
                obj.initiator.id,
                obj.initiator.name
            )
        return '-'

    @admin.display(description='运行时长', ordering='started_at')
    def duration_display(self, obj):
        """运行时长显示"""
        if obj.is_completed:
            color = '#3498db'
        elif obj.is_suspended:
            color = '#f39c12'
        elif obj.is_running:
            color = '#27ae60'
        else:
            color = '#95a5a6'
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.duration_display
        )

    @admin.action(description='软删除选中流程')
    def soft_delete(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条流程实例')

    @admin.action(description='恢复选中流程')
    def restore(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条流程实例')

    @admin.action(description='挂起选中学员流程')
    def suspend_processes(self, request, queryset):
        count = queryset.filter(status='running').update(status='suspended')
        self.message_user(request, f'已挂起 {count} 条流程')

    @admin.action(description='终止选中学员流程')
    def terminate_processes(self, request, queryset):
        count = queryset.filter(status__in=['running', 'suspended']).update(status='terminated')
        self.message_user(request, f'已终止 {count} 条流程')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs


@admin.register(ProcessTask)
class ProcessTaskAdmin(admin.ModelAdmin):
    """流程任务模型的后台管理配置"""

    list_display = [
        'id', 'task_name', 'process_link', 'status_badge',
        'assignee_link', 'started_at', 'completed_at', 'is_deleted'
    ]

    search_fields = [
        'task_name', 'task_id', 'assignee__name',
        'process_instance__process_name'
    ]

    list_filter = [
        'status', 'is_deleted', 'created_at'
    ]

    ordering = ['-created_at']
    list_per_page = 20
    date_hierarchy = 'created_at'

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'process_instance', 'task_id', 'task_name')
        }),
        ('任务状态', {
            'fields': ('status', 'assignee')
        }),
        ('表单数据', {
            'fields': ('form_data', 'comment'),
            'classes': ('collapse',)
        }),
        ('时间记录', {
            'fields': ('started_at', 'completed_at')
        }),
        ('审计信息', {
            'fields': ('is_deleted', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'started_at', 'completed_at', 'created_at', 'updated_at']
    list_display_links = ['id', 'task_name']
    actions = ['soft_delete', 'restore', 'complete_tasks', 'cancel_tasks']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('process_instance', 'assignee')

    @admin.display(description='流程', ordering='process_instance__process_name')
    def process_link(self, obj):
        return format_html(
            '<a href="/admin/workflow_app/processinstance/{}/change/">{}</a>',
            obj.process_instance.id,
            obj.process_instance.process_name
        )

    @admin.display(description='状态', ordering='status')
    def status_badge(self, obj):
        color_map = {
            'pending': '#95a5a6',
            'in_progress': '#3498db',
            'completed': '#27ae60',
            'cancelled': '#e74c3c',
            'rejected': '#f39c12',
        }
        color = color_map.get(obj.status, '#95a5a6')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )

    @admin.display(description='办理人', ordering='assignee__name')
    def assignee_link(self, obj):
        if obj.assignee:
            return format_html(
                '<a href="/admin/organization_app/personnel/{}/change/">{}</a>',
                obj.assignee.id,
                obj.assignee.name
            )
        return '-'

    @admin.action(description='软删除选中任务')
    def soft_delete(self, request, queryset):
        count = queryset.update(is_deleted=True)
        self.message_user(request, f'成功软删除 {count} 条任务')

    @admin.action(description='恢复选中任务')
    def restore(self, request, queryset):
        count = queryset.update(is_deleted=False)
        self.message_user(request, f'成功恢复 {count} 条任务')

    @admin.action(description='完成选中任务')
    def complete_tasks(self, request, queryset):
        count = queryset.filter(status__in=['pending', 'in_progress']).update(status='completed')
        self.message_user(request, f'已完成 {count} 条任务')

    @admin.action(description='取消选中任务')
    def cancel_tasks(self, request, queryset):
        count = queryset.filter(status__in=['pending', 'in_progress']).update(status='cancelled')
        self.message_user(request, f'已取消 {count} 条任务')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(is_deleted=False)
        return qs
