# -*- coding: utf-8 -*-
"""
audit_app - 审计追踪模块

包含：AuditLog（审计日志）模型
"""

from django.db import models


class AuditLog(models.Model):
    """
    审计日志模型

    记录所有关键业务操作的审计日志，包括：
    - 操作人员
    - 操作动作
    - 资源类型和ID
    - 状态变更前后
    - 请求上下文（IP、User-Agent）
    """

    id = models.BigAutoField(primary_key=True)
    process_instance = models.ForeignKey(
        'workflow_app.ProcessInstance',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='流程实例'
    )
    operator = models.ForeignKey(
        'organization_app.Personnel',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='操作人员'
    )
    action = models.CharField(max_length=50, db_index=True, verbose_name='操作动作')
    before_state = models.JSONField(null=True, blank=True, verbose_name='变更前状态')
    after_state = models.JSONField(null=True, blank=True, verbose_name='变更后状态')
    comment = models.TextField(blank=True, verbose_name='备注')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.TextField(blank=True, verbose_name='User-Agent')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '审计日志'
        verbose_name_plural = '审计日志列表'
        indexes = [
            models.Index(fields=['action']),
            models.Index(fields=['operator', 'created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        operator_name = self.operator.name if self.operator else '系统'
        return f"{operator_name} - {self.action} @ {self.created_at}"
