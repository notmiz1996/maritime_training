"""
组织架构模块 - Organization 模型

参考：后端开发与验收手册 2.2.1 Organization（组织架构）
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from loguru import logger


class Organization(models.Model):
    """
    组织架构模型

    支持多级组织结构（公司 -> 部门 -> 办公室），通过 parent 指定父级，
    自动计算 level（层级深度）和 path（路径）字段。

    软删除设计：is_deleted=True 的记录不参与默认查询。
    """

    # ========== 基本信息字段 ==========
    ORG_TYPE_CHOICES = [
        ('company', '公司'),
        ('department', '部门'),
        ('office', '办公室'),
    ]

    id = models.BigAutoField(
        primary_key=True,
        verbose_name='组织ID',
        help_text='组织唯一标识符'
    )

    name = models.CharField(
        max_length=100,
        verbose_name='组织名称',
        help_text='请输入组织全称（如"华东航运公司"）'
    )

    org_type = models.CharField(
        max_length=20,
        choices=ORG_TYPE_CHOICES,
        verbose_name='组织类型',
        help_text='选择组织的类型：公司、部门或办公室'
    )

    # ========== 层级结构字段 ==========
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='上级组织',
        help_text='选择上级组织，顶级组织无需选择'
    )

    level = models.PositiveIntegerField(
        default=0,
        verbose_name='层级深度',
        help_text='自动计算，用于前端展示树形结构深度'
    )

    path = models.CharField(
        max_length=500,
        db_index=True,
        verbose_name='组织路径',
        help_text='自动生成，格式如 /company1/dept2/office3'
    )

    # ========== 审计字段 ==========
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='是否删除',
        help_text='软删除标记，True 表示已删除'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        help_text='自动记录创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        help_text='自动记录最后修改时间'
    )

    class Meta:
        ordering = ['path']
        verbose_name = '组织'
        verbose_name_plural = '组织列表'

    def __str__(self):
        return f"{self.name} ({self.get_org_type_display()})"

    def save(self, *args, **kwargs):
        """保存时自动计算 level 和 path"""
        # 计算 level
        if self.parent:
            self.level = self.parent.level + 1
            if self.level > 10:
                raise ValidationError("组织层级不能超过 10 级")
        else:
            self.level = 0

        # 计算 path
        if self.pk:
            # 已存在，直接计算 path
            self.path = f"/{self.pk}" if self.parent is None else f"{self.parent.path}/{self.pk}"
        else:
            # 新建时，先保存获取 pk，再计算 path
            super().save(*args, **kwargs)  # 第一次保存（INSERT）
            self.path = f"/{self.pk}" if self.parent is None else f"{self.parent.path}/{self.pk}"
            # 只更新 path 字段
            super().save(update_fields=['path'])
            return  # 重要：避免再次保存

        # 更新时
        super().save(*args, **kwargs)

    def clean(self):
        if self.level > 10:
            raise ValidationError({'level': '组织层级不能超过 10 级'})


class Personnel(models.Model):
    """
    人员模型

    关联 User 模型，一对一关系。一个用户对应一个人员记录。
    通过 organization 关联到组织，支持多职务（通过 PersonnelPosition）。

    软删除设计：is_deleted=True 的记录不参与默认查询。
    """

    # ========== 基本信息字段 ==========
    id = models.BigAutoField(
        primary_key=True,
        verbose_name='人员ID',
        help_text='人员唯一标识符'
    )

    # 关联 User（一对一，删除 User 时级联删除 Personnel）
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='personnel',
        verbose_name='关联用户',
        help_text='关联系统用户，删除用户时人员记录一并删除'
    )

    # 姓名
    name = models.CharField(
        max_length=100,
        verbose_name='姓名',
        help_text='请输入人员真实姓名'
    )

    # 身份证号（存储原始数据，前端脱敏展示）
    id_card = models.CharField(
        max_length=18,
        unique=True,
        verbose_name='身份证号码',
        help_text='格式为18位身份证号，最后一位可为 X'
    )

    # 手机号
    phone = models.CharField(
        max_length=20,
        verbose_name='手机号码',
        help_text='请输入11位手机号'
    )

    # ========== 组织关联字段 ==========
    # 所属组织（PROTECT 保护：不能删除有人员归属的组织）
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name='personnels',
        verbose_name='所属组织',
        help_text='选择人员所属的组织'
    )

    # ========== 审计字段 ==========
    is_deleted = models.BooleanField(
        default=False,
        verbose_name='是否删除',
        help_text='软删除标记，True 表示已删除'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        help_text='自动记录创建时间'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        help_text='自动记录最后修改时间'
    )

    class Meta:
        ordering = ['name']
        verbose_name = '人员'
        verbose_name_plural = '人员列表'

    def __str__(self):
        return self.name

    def clean(self):
        """校验身份证格式"""
        if self.id_card:
            # 18位身份证校验
            if len(self.id_card) != 18:
                raise ValidationError({'id_card': '身份证号必须为18位'})
            # 最后一位可以是 X（不区分大小写）
            if not self.id_card[-1].isdigit() and self.id_card[-1].upper() != 'X':
                raise ValidationError({'id_card': '身份证号格式不正确'})

class Position(models.Model):
    """职务模型"""

    id = models.BigAutoField(primary_key=True, verbose_name='职务ID', help_text='职务唯一标识符')
    name = models.CharField(
        max_length=50,
        verbose_name='职务名称',
        help_text='请输入职务名称，如"船长"、"大副"'
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='职务编码',
        help_text='请输入唯一的职务编码，如"CAPTAIN"、"FIRST_MATE"'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        verbose_name='所属组织',
        help_text='选择职务所属的组织'
    )
    permissions = models.ManyToManyField(
        'auth.Permission',
        blank=True,
        verbose_name='权限列表',
        related_name='positions',
    )
    is_concurrentable = models.BooleanField(
        default=True,
        verbose_name='允许兼职',
        help_text='是否允许人员兼任此职务'
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
        ordering = ['organization__path', 'code']
        verbose_name = '职务'
        verbose_name_plural = '职务列表'

    def __str__(self):
        return f"{self.name} ({self.code})"

class PersonnelPosition(models.Model):
    """人员-职务关联模型"""

    id = models.BigAutoField(primary_key=True, verbose_name='记录ID', help_text='关联记录唯一标识符')
    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        verbose_name='人员',
        help_text='选择人员'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.CASCADE,
        verbose_name='职务',
        help_text='选择职务'
    )
    is_primary = models.BooleanField(
        default=False,
        verbose_name='主职务',
        help_text='是否为主职务（一个人只能有一个主职务）'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='生效中',
        help_text='是否生效'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        help_text='自动记录'
    )

    class Meta:
        unique_together = ['personnel', 'position']
        ordering = ['-is_primary', '-created_at']
        verbose_name = '人员职务'
        verbose_name_plural = '人员职务列表'

    def __str__(self):
        primary_tag = '★' if self.is_primary else ''
        return f"{self.personnel.name} - {self.position.name} {primary_tag}"

    def save(self, *args, **kwargs):
        """如果设置为主职务，自动取消同人员其他主职务标记"""
        if self.is_primary:
            PersonnelPosition.objects.filter(
                personnel=self.personnel,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
