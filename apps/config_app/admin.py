# -*- coding: utf-8 -*-
"""
config_app Django Admin 配置

包含：SystemConfig 的 Admin 配置
"""

from django.contrib import admin

from .models import SystemConfig


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    """系统配置模型的后台管理配置"""

    list_display = [
        'id', 'key', 'value_display', 'group', 'is_active', 'updated_by', 'updated_at'
    ]
    search_fields = ['key', 'group', 'description']
    list_filter = ['group', 'is_active']
    ordering = ['group', 'key']
    list_per_page = 50

    fieldsets = (
        ('基本信息', {
            'fields': ('id', 'key', 'value', 'group')
        }),
        ('详情', {
            'fields': ('description', 'is_active')
        }),
        ('审计信息', {
            'fields': ('updated_by', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    readonly_fields = ['id', 'updated_at']

    def value_display(self, obj):
        return str(obj.value)[:50]
    value_display.short_description = '配置值'
