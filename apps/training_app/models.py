# -*- coding: utf-8 -*-
"""
training_app - 培训管理模块

包含：培训类型、培训班、培训班-学员关联模型
"""

from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils.html import format_html


class TrainingType(models.Model):
    """培训类型模型"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name='培训类型ID',
        help_text='培训类型唯一标识符'
    )
    name = models.CharField(
        max_length=50,
        verbose_name='培训类型名称',
        help_text='请输入培训类型名称，如"船员基本安全培训"'
    )
    category = models.CharField(
        max_length=20,
        verbose_name='分类',
        help_text='岗位/职务分类，如"驾驶岗位"、"轮机岗位"'
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='上级类型',
        help_text='选择上级培训类型，支持多级分类'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='是否删除',
        help_text='软删除标记'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        help_text='自动记录'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        help_text='自动更新'
    )

    class Meta:
        ordering = ['category', 'name']
        verbose_name = '培训类型'
        verbose_name_plural = '培训类型列表'

    def __str__(self):
        return f"{self.name} ({self.category})"

    def clean(self):
        """禁止循环引用"""
        if self.parent:
            ancestor = self.parent
            while ancestor:
                if ancestor == self:
                    raise ValidationError({'parent': '不能将自身或下级类型设为上级类型'})
                ancestor = ancestor.parent


class TrainingClass(models.Model):
    """培训班模型"""

    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('submitted', '已提交'),
        ('approved', '已审批'),
        ('in_progress', '进行中'),
        ('completed', '已完成'),
        ('archived', '已归档'),
    ]

    id = models.BigAutoField(
        primary_key=True,
        verbose_name='班级ID',
        help_text='培训班唯一标识符'
    )
    class_no = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        verbose_name='班级编号',
        help_text='请输入唯一的班级编号'
    )
    maritime_system_no = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='海事局系统编号',
        help_text='海事局系统编号，允许为空，但不允许重复'
    )
    training_type = models.ForeignKey(
        TrainingType,
        on_delete=models.PROTECT,
        verbose_name='培训类型',
        help_text='选择培训班对应的培训类型'
    )
    start_date = models.DateField(
        verbose_name='开始日期',
        help_text='请选择培训班开始日期'
    )
    end_date = models.DateField(
        verbose_name='结束日期',
        help_text='请选择培训班结束日期'
    )
    total_days = models.PositiveIntegerField(
        default=1,
        verbose_name='总天数',
        help_text='自动计算：结束日期 - 开始日期 + 1'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True,
        verbose_name='状态',
        help_text='班级当前状态，状态流转由工作流引擎驱动'
    )
    required_attendance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=90.00,
        verbose_name='必需出勤率',
        help_text='最低出勤率要求，范围 0.00 ~ 999.99，单位：%'
    )
    created_by = models.ForeignKey(
        'organization_app.Personnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='创建人',
        help_text='自动记录'
    )
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='是否删除',
        help_text='软删除标记'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        help_text='自动记录'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        help_text='自动更新'
    )

    # 签到配置
    checkin_enabled = models.BooleanField(
        default=False,
        verbose_name='启用签到',
        help_text='是否启用扫码签到功能'
    )
    require_location = models.BooleanField(
        default=False,
        verbose_name='要求位置签到',
        help_text='是否要求在指定位置范围内签到'
    )
    location_radius = models.IntegerField(
        default=200,
        verbose_name='签到半径',
        help_text='允许签到的范围半径，单位：米'
    )
    training_location_lat = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='培训地点纬度',
        help_text='培训地点纬度坐标，精度约 0.01米'
    )
    training_location_lng = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        verbose_name='培训地点经度',
        help_text='培训地点经度坐标，精度约 0.01米'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = '培训班'
        verbose_name_plural = '培训班列表'

    def __str__(self):
        return f"{self.class_no} ({self.get_status_display()})"

    def clean(self):
        """校验日期范围"""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({'end_date': '结束日期必须大于或等于开始日期'})

    def save(self, *args, **kwargs):
        """自动计算 total_days"""
        if self.start_date and self.end_date:
            self.total_days = (self.end_date - self.start_date).days + 1
            if self.total_days < 1:
                raise ValueError("结束日期必须大于开始日期")
        super().save(*args, **kwargs)


class TrainingClassStudent(models.Model):
    """培训班-学员关联模型"""

    ENROLLMENT_STATUS_CHOICES = [
        ('pending', '报名待审'),
        ('first_review', '资格初审'),
        ('second_review', '复审'),
        ('confirmed', '已确认'),
        ('rejected', '已拒绝'),
    ]

    id = models.BigAutoField(
        primary_key=True,
        verbose_name='记录ID',
        help_text='关联记录唯一标识符'
    )
    training_class = models.ForeignKey(
        TrainingClass,
        on_delete=models.CASCADE,
        verbose_name='培训班',
        help_text='选择报名的培训班'
    )
    student = models.ForeignKey(
        'student_app.Student',
        on_delete=models.CASCADE,
        verbose_name='学员',
        help_text='选择报名的学员'
    )
    enrollment_status = models.CharField(
        max_length=20,
        choices=ENROLLMENT_STATUS_CHOICES,
        default='pending',
        db_index=True,
        verbose_name='报名状态',
        help_text='学员报名审核状态'
    )
    attendance_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name='出勤率',
        help_text='学员出勤率，范围 0.00 ~ 999.99，单位：%'
    )
    certificate_issued = models.BooleanField(
        default=False,
        verbose_name='已发证',
        help_text='是否已发放培训证书'
    )
    certificate_no = models.CharField(
        max_length=64,
        blank=True,
        verbose_name='证书编号',
        help_text='发放证书的编号，未发放时为空'
    )
    enrolled_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='报名时间',
        help_text='自动记录'
    )

    class Meta:
        unique_together = ['training_class', 'student']
        ordering = ['-enrolled_at']
        verbose_name = '报名记录'
        verbose_name_plural = '报名记录列表'

    def __str__(self):
        return f"{self.student.name} - {self.training_class.class_no}"

    def clean(self):
        """校验出勤率范围"""
        if self.attendance_rate < 0 or self.attendance_rate > 999.99:
            raise ValidationError({'attendance_rate': '出勤率必须在 0.00 ~ 999.99 范围内'})


class CourseSchedule(models.Model):
    """
    课程安排模型

    记录每个培训班的每日课程安排，包括课程名称、时间、地点等信息。
    一个培训班包含多个课程安排，通过 ForeignKey 关联。

    课程类型：
    - theory：理论课
    - practical：实操课
    - exam：考试
    - assessment：评估
    """

    COURSE_TYPE_CHOICES = [
        ('theory', '理论课'),
        ('practical', '实操课'),
        ('exam', '考试'),
        ('assessment', '评估'),
    ]

    SESSION_CHOICES = [
        ('morning', '上午'),
        ('afternoon', '下午'),
        ('evening', '晚上'),
        ('full_day', '全天'),
    ]

    id = models.UUIDField(
        primary_key=True,
        editable=False,
        verbose_name='课程ID',
        help_text='课程安排唯一标识符'
    )
    training_class = models.ForeignKey(
        TrainingClass,
        on_delete=models.CASCADE,
        related_name='course_schedules',
        verbose_name='所属班级',
        help_text='课程所属的培训班'
    )
    course_name = models.CharField(
        max_length=200,
        verbose_name='课程名称',
        help_text='请输入课程名称，如"海上救生设备操作"'
    )
    course_type = models.CharField(
        max_length=20,
        choices=COURSE_TYPE_CHOICES,
        verbose_name='课程类型',
        help_text='theory=理论课, practical=实操课, exam=考试, assessment=评估'
    )
    teacher = models.CharField(
        max_length=100,
        verbose_name='授课教师',
        help_text='授课教师姓名'
    )
    teacher_contact = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='教师联系方式',
        help_text='授课教师联系方式'
    )
    date = models.DateField(
        verbose_name='课程日期',
        help_text='课程安排的日期'
    )
    session = models.CharField(
        max_length=10,
        choices=SESSION_CHOICES,
        verbose_name='场次',
        help_text='morning=上午, afternoon=下午, evening=晚上, full_day=全天'
    )
    start_time = models.TimeField(
        verbose_name='开始时间',
        help_text='课程开始时间'
    )
    end_time = models.TimeField(
        verbose_name='结束时间',
        help_text='课程结束时间'
    )
    location = models.CharField(
        max_length=200,
        verbose_name='上课地点',
        help_text='上课地点/教室，如"A101教室"或"实操场地1"'
    )
    max_attendees = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        verbose_name='最大人数',
        help_text='本课程最大容纳人数，不填则跟随班级设置'
    )
    credit_hours = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        verbose_name='学分/学时',
        help_text='本课程对应的学分或学时数'
    )
    description = models.TextField(
        blank=True,
        verbose_name='课程简介',
        help_text='课程的详细说明'
    )
    materials = models.TextField(
        blank=True,
        verbose_name='所需教材/材料',
        help_text='本课程需要的教材或材料清单'
    )
    prerequisite = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='先修课程',
        help_text='本课程的先修课程要求'
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
        db_table = 'course_schedule'
        ordering = ['date', 'start_time', 'session']
        verbose_name = '课程安排'
        verbose_name_plural = '课程安排列表'
        indexes = [
            models.Index(fields=['training_class', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['course_type']),
            models.Index(fields=['teacher']),
            models.Index(fields=['-date']),
        ]

    def __str__(self):
        return f"{self.course_name} - {self.date} {self.get_session_display()}"

    def clean(self):
        """校验课程安排数据"""
        errors = {}

        # 结束时间不能早于开始时间
        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                errors['end_time'] = '结束时间不能早于开始时间'

        # 课程日期不能超出班级日期范围
        if self.training_class and self.date:
            if self.date < self.training_class.start_date or self.date > self.training_class.end_date:
                errors[
                    'date'] = f'课程日期必须在班级日期范围内（{self.training_class.start_date} 至 {self.training_class.end_date}）'

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
