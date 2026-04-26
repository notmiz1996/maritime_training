"""
attendance_app - 考勤管理模块

考勤记录模型：记录学员每天每场次的考勤状态
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class AttendanceRecord(models.Model):
    """
    考勤记录模型

    记录每个学员每天每场次（上午/下午）的考勤状态。
    复合唯一约束确保同一学员在同一班级、同一日期、同一场次只有一条记录。

    考勤状态：
    - present：正常签到
    - late：迟到
    - absent：缺勤
    - leave：请假（需关联已审批的请假申请）
    """

    SESSION_CHOICES = [
        ('morning', '上午'),
        ('afternoon', '下午'),
    ]

    STATUS_CHOICES = [
        ('present', '正常签到'),
        ('late', '迟到'),
        ('absent', '缺勤'),
        ('leave', '请假'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='考勤记录ID',
        help_text='考勤记录唯一标识符'
    )
    training_class = models.ForeignKey(
        'training_app.TrainingClass',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name='所属班级',
        help_text='学员所属的培训班'
    )
    student = models.ForeignKey(
        'student_app.Student',
        on_delete=models.CASCADE,
        related_name='attendance_records',
        verbose_name='学员',
        help_text='进行考勤的学员'
    )
    course_schedule = models.ForeignKey(
        'training_app.CourseSchedule',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='attendance_records',
        verbose_name='关联课程',
        help_text='关联的课程安排，可为空（如随机考勤）'
    )
    date = models.DateField(
        verbose_name='考勤日期',
        help_text='进行考勤的日期'
    )
    session = models.CharField(
        max_length=10,
        choices=SESSION_CHOICES,
        verbose_name='场次',
        help_text='上午或下午'
    )
    check_in = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='签到时间',
        help_text='学员签到时间'
    )
    check_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='签退时间',
        help_text='学员签退时间'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='absent',
        db_index=True,
        verbose_name='考勤状态',
        help_text='present=正常签到, late=迟到, absent=缺勤, leave=请假'
    )
    remark = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='备注',
        help_text='特殊情况说明，如迟到原因等'
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
        db_table = 'attendance_record'
        unique_together = ['training_class', 'student', 'date', 'session']
        ordering = ['-date', '-session', 'student']
        verbose_name = '考勤记录'
        verbose_name_plural = '考勤记录列表'
        indexes = [
            models.Index(fields=['training_class', 'date', 'session']),
            models.Index(fields=['student', 'date']),
            models.Index(fields=['status']),
            models.Index(fields=['-date']),
        ]

    def __str__(self):
        return f"{self.student.name} - {self.date} {self.get_session_display()}"

    def clean(self):
        """校验考勤数据"""
        errors = {}

        # 签到时间不能晚于签退时间
        if self.check_in and self.check_out:
            if self.check_in > self.check_out:
                errors['check_in'] = '签到时间不能晚于签退时间'

        # 迟到必须有时间记录
        if self.status == 'late' and not self.check_in:
            errors['status'] = '迟到状态必须记录签到时间'

        # 请假必须有备注说明
        if self.status == 'leave' and not self.remark:
            errors['remark'] = '请假状态必须填写原因'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_present(self):
        """是否出勤（含正常签到和迟到）"""
        return self.status in ['present', 'late']

    @property
    def is_absence(self):
        """是否缺勤"""
        return self.status == 'absent'

    @property
    def is_leave(self):
        """是否请假"""
        return self.status == 'leave'

    @property
    def duration_minutes(self):
        """出勤时长（分钟）"""
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            return int(delta.total_seconds() / 60)
        return 0