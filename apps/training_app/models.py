from django.db import models
from django.core.exceptions import ValidationError


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
