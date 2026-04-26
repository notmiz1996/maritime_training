# -*- coding: utf-8 -*-
"""
workflow_app - 工作流管理模块

流程实例模型：记录 SpiffWorkflow 运行时实例
"""

import uuid

from django.db import models
from django.utils import timezone


class ProcessInstance(models.Model):
    """
    流程实例模型

    存储 SpiffWorkflow 运行时实例，记录每个流程的启动、执行、完成状态。

    状态说明：
    - running：运行中
    - suspended：已挂起
    - completed：已完成
    - terminated：已终止
    """

    STATUS_CHOICES = [
        ('running', '运行中'),
        ('suspended', '已挂起'),
        ('completed', '已完成'),
        ('terminated', '已终止'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='流程实例ID',
        help_text='流程实例唯一标识符'
    )
    process_key = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name='流程定义Key',
        help_text='流程定义标识，如"training_class_flow"'
    )
    process_name = models.CharField(
        max_length=200,
        verbose_name='流程名称',
        help_text='流程实例显示名称'
    )
    bpmn_file = models.CharField(
        max_length=255,
        verbose_name='BPMN文件路径',
        help_text='关联的BPMN流程文件路径'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='running',
        db_index=True,
        verbose_name='流程状态',
        help_text='running=运行中, suspended=已挂起, completed=已完成, terminated=已终止'
    )
    current_task_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='当前任务ID',
        help_text='当前执行的任务节点ID'
    )
    current_task_name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='当前任务名称',
        help_text='当前执行的任务节点名称'
    )
    variables = models.JSONField(
        default=dict,
        verbose_name='流程变量',
        help_text='存储流程执行过程中的变量数据（JSON格式）'
    )
    initiator = models.ForeignKey(
        'organization_app.Personnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='initiated_processes',
        verbose_name='发起人',
        help_text='启动该流程的用户'
    )
    related_object_type = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='关联对象类型',
        help_text='关联的业务对象类型，如 TrainingClass、Student'
    )
    related_object_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='关联对象ID',
        help_text='关联的业务对象ID'
    )
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='启动时间',
        help_text='流程启动时间'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间',
        help_text='流程完成时间'
    )
    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='挂起时间',
        help_text='流程挂起时间'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='已删除',
        help_text='软删除标记'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        help_text='记录创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        help_text='最后更新时间'
    )

    class Meta:
        db_table = 'process_instance'
        ordering = ['-created_at']
        verbose_name = '流程实例'
        verbose_name_plural = '流程实例列表'
        indexes = [
            models.Index(fields=['process_key', 'status']),
            models.Index(fields=['initiator', 'status']),
            models.Index(fields=['related_object_type', 'related_object_id']),
            models.Index(fields=['status', '-started_at']),
            models.Index(fields=['-started_at']),
        ]

    def __str__(self):
        return f"{self.process_name} - {self.id} ({self.get_status_display()})"

    def clean(self):
        """校验流程实例数据"""
        errors = {}

        # 已完成的流程不能再运行
        if self.status == 'completed' and self.current_task_id:
            errors['status'] = '已完成的流程不能有当前任务'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        # 自动设置完成时间
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        # 自动设置挂起时间
        if self.status == 'suspended' and not self.suspended_at:
            self.suspended_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_running(self):
        """是否运行中"""
        return self.status == 'running'

    @property
    def is_completed(self):
        """是否已完成"""
        return self.status == 'completed'

    @property
    def is_suspended(self):
        """是否已挂起"""
        return self.status == 'suspended'

    @property
    def duration_seconds(self):
        """运行时长（秒）"""
        if self.started_at:
            end = self.completed_at or timezone.now()
            return int((end - self.started_at).total_seconds())
        return 0

    @property
    def duration_display(self):
        """运行时长（人类可读格式）"""
        seconds = self.duration_seconds
        if seconds < 60:
            return f"{seconds}秒"
        elif seconds < 3600:
            return f"{seconds // 60}分钟"
        elif seconds < 86400:
            return f"{seconds // 3600}小时{seconds % 3600 // 60}分钟"
        else:
            return f"{seconds // 86400}天{seconds % 86400 // 3600}小时"


class ProcessTask(models.Model):
    """
    流程任务模型

    记录流程实例中的每个任务节点执行情况。
    """

    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('in_progress', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('rejected', '已拒绝'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='任务ID',
        help_text='任务唯一标识符'
    )
    process_instance = models.ForeignKey(
        ProcessInstance,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name='所属流程实例',
        help_text='所属的流程实例'
    )
    task_id = models.CharField(
        max_length=100,
        verbose_name='任务节点ID',
        help_text='BPMN中的任务节点ID'
    )
    task_name = models.CharField(
        max_length=200,
        verbose_name='任务名称',
        help_text='任务节点名称'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='任务状态',
        help_text='pending=待处理, in_progress=处理中, completed=已完成, cancelled=已取消, rejected=已拒绝'
    )
    assignee = models.ForeignKey(
        'organization_app.Personnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name='办理人',
        help_text='任务当前办理人'
    )
    form_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='表单数据',
        help_text='任务提交的表单数据（JSON格式）'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='处理意见',
        help_text='任务处理时的意见说明'
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='开始时间',
        help_text='任务开始处理时间'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='完成时间',
        help_text='任务完成时间'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='已删除',
        help_text='软删除标记'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        help_text='记录创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        help_text='最后更新时间'
    )

    class Meta:
        db_table = 'process_task'
        ordering = ['created_at']
        verbose_name = '流程任务'
        verbose_name_plural = '流程任务列表'
        indexes = [
            models.Index(fields=['process_instance', 'status']),
            models.Index(fields=['assignee', 'status']),
            models.Index(fields=['task_id']),
        ]

    def __str__(self):
        return f"{self.task_name} - {self.status}"

    @property
    def is_pending(self):
        """是否待处理"""
        return self.status == 'pending'

    @property
    def is_completed(self):
        """是否已完成"""
        return self.status == 'completed'
