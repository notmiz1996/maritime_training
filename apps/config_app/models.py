# -*- coding: utf-8 -*-
"""
config_app - 系统配置模块

包含：SystemConfig（系统配置）模型
"""

from django.db import models


class SystemConfig(models.Model):
    """
    系统配置模型

    存储系统级配置项，以 JSON 形式存储灵活的值。

    预置配置项：
    - leave_approval_threshold_days: 请假审批阈值（天）
    - certificate_validity_years: 证书有效期（年）
    - required_attendance_rate: 必需出勤率（%）
    - checkin_secret_key: 扫码签到签名密钥
    - checkin_code_expires: 二维码有效期（秒）
    - checkin_location_required: 是否强制定位
    - checkin_location_radius: 签到允许范围（米）
    """

    id = models.BigAutoField(primary_key=True)
    key = models.CharField(max_length=100, unique=True, db_index=True, verbose_name='配置键')
    value = models.JSONField(verbose_name='配置值')
    group = models.CharField(max_length=50, db_index=True, verbose_name='配置分组')
    description = models.TextField(blank=True, verbose_name='描述')
    is_active = models.BooleanField(default=True, verbose_name='是否激活')
    updated_by = models.ForeignKey(
        'organization_app.Personnel',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='更新人'
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['group', 'key']
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置列表'

    def __str__(self):
        return f"{self.key} = {self.value}"

    @classmethod
    def get_value(cls, key, default=None):
        """获取配置值，带默认值"""
        try:
            config = cls.objects.get(key=key, is_active=True)
            return config.value
        except cls.DoesNotExist:
            return default
