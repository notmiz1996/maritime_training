from django.core.exceptions import ValidationError
from django.db import models


class Student(models.Model):
    """学员模型"""

    id = models.BigAutoField(
        primary_key=True,
        verbose_name='学员ID',
        help_text='学员唯一标识符'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='姓名',
        help_text='请输入学员的法定姓名'
    )
    id_card = models.CharField(
        max_length=18,
        unique=True,
        verbose_name='身份证号码',
        help_text='请输入18位身份证号，格式为18位数字或末位为X'
    )
    phone = models.CharField(
        max_length=20,
        verbose_name='手机号码',
        help_text='请输入学员的手机号码'
    )

    # 四级地址字段（按要求拆分）
    province = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='省份/直辖市',
        help_text='请选择或输入省份/直辖市'
    )
    city = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='城市/地级市',
        help_text='请选择或输入城市/地级市'
    )
    district = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='区/县',
        help_text='请选择或输入区/县'
    )
    detail_address = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='详细地址',
        help_text='请输入详细地址，如街道、门牌号'
    )

    photo_url = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='照片URL',
        help_text='学员证件照的访问地址'
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
        ordering = ['name']
        verbose_name = '学员'
        verbose_name_plural = '学员列表'

    def __str__(self):
        return self.name

    def clean(self):
        """身份证格式校验"""
        import re
        if self.id_card:
            pattern = r'^\d{17}[\dXx]$'
            if not re.match(pattern, self.id_card):
                raise ValidationError({'id_card': '身份证号格式不正确，应为18位'})

    @property
    def full_address(self):
        """返回完整地址字符串"""
        parts = [p for p in [self.province, self.city, self.district, self.detail_address] if p]
        return ''.join(parts) if parts else ''

