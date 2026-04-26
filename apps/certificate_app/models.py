# -*- coding: utf-8 -*-
"""
certificate_app - 证书管理模块

培训证书模型：记录学员培训完成后获得的证书信息
"""

import uuid
from datetime import date, timedelta

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Certificate(models.Model):
    """
    培训证书模型

    记录学员完成培训后获得的证书信息，包括证书编号、有效期、状态等。
    通过 idem_key 实现幂等，防止重复发放。

    状态说明：
    - issued：已发放
    - revoked：已撤销
    - lost：已挂失
    """

    STATUS_CHOICES = [
        ('issued', '已发放'),
        ('revoked', '已撤销'),
        ('lost', '已挂失'),
    ]

    VALIDITY_YEARS = 3  # 证书有效期：3年

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='证书ID',
        help_text='证书唯一标识符'
    )
    certificate_no = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name='证书编号',
        help_text='请输入唯一的证书编号'
    )
    student = models.ForeignKey(
        'student_app.Student',
        on_delete=models.CASCADE,
        related_name='certificates',
        verbose_name='学员',
        help_text='获得证书的学员'
    )
    training_class = models.ForeignKey(
        'training_app.TrainingClass',
        on_delete=models.PROTECT,
        related_name='certificates',
        verbose_name='所属培训班',
        help_text='完成培训的培训班'
    )
    training_type = models.ForeignKey(
        'training_app.TrainingType',
        on_delete=models.PROTECT,
        related_name='certificates',
        verbose_name='培训类型',
        help_text='证书对应的培训类型'
    )
    issued_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='发放时间',
        help_text='证书发放时间，系统自动记录'
    )
    validity_start = models.DateField(
        verbose_name='有效期开始',
        help_text='证书有效期开始日期'
    )
    validity_end = models.DateField(
        verbose_name='有效期结束',
        help_text='证书有效期结束日期'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='issued',
        db_index=True,
        verbose_name='证书状态',
        help_text='issued=已发放, revoked=已撤销, lost=已挂失'
    )
    idem_key = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        verbose_name='幂等键',
        help_text='用于防止重复发放，由学员ID+培训班ID+培训类型ID组合生成'
    )
    revoke_reason = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='撤销/挂失原因',
        help_text='撤销或挂失证书时的原因说明'
    )
    issued_by = models.ForeignKey(
        'organization_app.Personnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_certificates',
        verbose_name='发证人',
        help_text='发放证书的操作人员'
    )
    remark = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='备注',
        help_text='特殊情况说明'
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
        db_table = 'certificate'
        ordering = ['-issued_at']
        verbose_name = '培训证书'
        verbose_name_plural = '培训证书列表'
        indexes = [
            models.Index(fields=['student', 'training_class']),
            models.Index(fields=['training_type']),
            models.Index(fields=['status']),
            models.Index(fields=['validity_end']),
            models.Index(fields=['-issued_at']),
        ]

    def __str__(self):
        return f"{self.certificate_no} - {self.student.name}"

    def clean(self):
        """校验证书数据"""
        errors = {}

        # 有效期结束不能早于开始
        if self.validity_start and self.validity_end:
            if self.validity_end < self.validity_start:
                errors['validity_end'] = '有效期结束日期不能早于开始日期'

        # 撤销/挂失必须填写原因
        if self.status in ['revoked', 'lost'] and not self.revoke_reason:
            errors['revoke_reason'] = '撤销或挂失证书必须填写原因'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        """自动设置有效期"""
        if self.validity_start and not self.validity_end:
            self.validity_end = self.validity_start + timedelta(days=self.VALIDITY_YEARS * 365)
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_valid(self):
        """证书是否有效"""
        today = date.today()
        return (
                self.status == 'issued'
                and self.validity_start <= today <= self.validity_end
                and not self.is_deleted
        )

    @property
    def is_expired(self):
        """证书是否已过期"""
        return date.today() > self.validity_end

    @property
    def days_to_expire(self):
        """距离过期天数"""
        if self.is_expired:
            return 0
        return (self.validity_end - date.today()).days

    @staticmethod
    def generate_idem_key(student_id, training_class_id, training_type_id):
        """生成幂等键"""
        return f"{student_id}_{training_class_id}_{training_type_id}"
