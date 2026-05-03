#### -*- coding: utf-8 -*-
"""
organization_app - Service 层

职责：
- 封装业务逻辑
- 数据校验
- 日志记录
- 事务管理

架构原则：
- 所有业务逻辑必须经过 Service 层
- View 层禁止直接操作 Model
"""

from django.db import transaction
from django.core.exceptions import ValidationError

from loguru import logger

from .models import Organization, Personnel, Position, PersonnelPosition


#### ========== OrganizationService ==========

class OrganizationService:
    """
    组织架构服务

    提供组织相关的业务逻辑：
    - 创建组织（自动计算 level 和 path）
    - 获取子树
    - 校验层级深度
    """

    @staticmethod
    def create_organization(name: str, org_type: str, parent_id: int = None, **kwargs) -> Organization:
        """
        创建组织

        Args:
            name: 组织名称
            org_type: 组织类型（company/department/office）
            parent_id: 上级组织ID（可选）
            **kwargs: 其他字段

        Returns:
            Organization: 创建的组织

        Raises:
            ValidationError: 校验失败时抛出
        """
        logger.info(f"[OrganizationService] 创建组织: name={name}, org_type={org_type}, parent_id={parent_id}")

        # 校验 org_type
        valid_org_types = ['company', 'department', 'office']
        if org_type not in valid_org_types:
            raise ValidationError(f'org_type 必须是 {valid_org_types} 之一')

        # 计算 level
        level = 0
        path = ""

        if parent_id:
            try:
                parent = Organization.objects.get(id=parent_id, is_deleted=False)
                level = parent.level + 1

                # 校验层级深度（不能超过10级）
                if level > 10:
                    raise ValidationError({'level': '组织层级不能超过10级'})

            except Organization.DoesNotExist:
                raise ValidationError({'parent': '上级组织不存在'})

        # 创建组织
        org = Organization.objects.create(
            name=name,
            org_type=org_type,
            parent_id=parent_id,
            level=level,
            path=path,  # Model.save() 会自动计算
            **kwargs
        )

        logger.success(f"[OrganizationService] 组织创建成功: id={org.id}, path={org.path}")
        return org

    @staticmethod
    def get_subtree(org_id: int, max_depth: int = 10) -> list[Organization]:
        """
        获取组织的子树（所有后代）

        Args:
            org_id: 根组织ID
            max_depth: 最大深度（默认10）

        Returns:
            list[Organization]: 子树组织列表
        """
        try:
            root = Organization.objects.get(id=org_id, is_deleted=False)
        except Organization.DoesNotExist:
            return []

        descendants = Organization.objects.filter(
            path__startswith=root.path,
            level__gt=root.level,
            level__lte=root.level + max_depth,
            is_deleted=False
        ).order_by('path')

        logger.info(f"[OrganizationService] 获取子树: root={org_id}, count={descendants.count()}")
        return list(descendants)

    @staticmethod
    def soft_delete(org_id: int) -> bool:
        """
        软删除组织（仅标记为删除，不物理删除）

        Args:
            org_id: 组织ID

        Returns:
            bool: 是否成功
        """
        try:
            org = Organization.objects.get(id=org_id, is_deleted=False)
            org.is_deleted = True
            org.save()
            # 递归软删除子组织
            children = Organization.objects.filter(parent=org, is_deleted=False)
            for child in children:
                OrganizationService.soft_delete(child.id)

            logger.success(f"[OrganizationService] 组织软删除成功: id={org_id}")
            return True

        except Organization.DoesNotExist:
            logger.warning(f"[OrganizationService] 组织不存在或已删除: id={org_id}")
            return False

    @staticmethod
    def validate_parent(parent_id: int, exclude_id: int = None) -> bool:
        """
        校验 parent 是否合法（不能形成环）
        Args:
            parent_id: 上级组织ID
            exclude_id: 排除的组织ID（如自身）

        Returns:
            bool: 是否合法
            """
        if not parent_id:
            return True

        # 检查 parent 是否是排除的组织自身
        if exclude_id and parent_id == exclude_id:
            logger.warning(f"[OrganizationService] 不能将自身设为上级组织")
            return False

        # 检查 parent 是否存在
        try:
            parent = Organization.objects.get(id=parent_id, is_deleted=False)
        except Organization.DoesNotExist:
            logger.warning(f"[OrganizationService] 上级组织不存在: id={parent_id}")
            return False

        return True


class PersonnelService:
    """
    人员管理服务
    提供人员相关的业务逻辑：
    - 创建人员（自动关联 User）
    - 分配职务
    - 移除职务
    """

    @staticmethod
    @transaction.atomic
    def create_personnel(name: str, id_card: str, phone: str, organization_id: int,
                         user_id: int = None, **kwargs) -> Personnel:
        """
        创建人员

        Args:
            name: 姓名
            id_card: 身份证号（18位）
            phone: 手机号
            organization_id: 组织ID
            user_id: 关联的 User ID（可选，数据库可能必填）
            **kwargs: 其他字段

        Returns:
            Personnel: 创建的人员
        """
        logger.info(f"[PersonnelService] 创建人员: name={name}, organization_id={organization_id}")

        # 校验身份证号格式
        if id_card and len(id_card) != 18:
            raise ValidationError({'id_card': '身份证号必须为18位'})

        # 校验组织存在
        try:
            org = Organization.objects.get(id=organization_id, is_deleted=False)
        except Organization.DoesNotExist:
            raise ValidationError({'organization': '组织不存在'})

        # 创建人员
        personnel = Personnel.objects.create(
            name=name,
            id_card=id_card,
            phone=phone,
            organization_id=organization_id,
            user_id=user_id,  # 如果 user_id=None 且数据库 NOT NULL 会报错
            **kwargs
        )

        logger.success(f"[PersonnelService] 人员创建成功: id={personnel.id}")
        return personnel


    @staticmethod
    @transaction.atomic
    def assign_position(personnel_id: int, position_id: int,
                        is_primary: bool = False) -> PersonnelPosition:
        """
        分配职务

        Args:
            personnel_id: 人员ID
            position_id: 职务ID
            is_primary: 是否为主职务

        Returns:
            PersonnelPosition: 创建的关联记录

        Raises:
            ValidationError: 校验失败时抛出
        """
        logger.info(f"[PersonnelService] 分配职务: personnel_id={personnel_id}, position_id={position_id}")

        # 校验人员存在
        try:
            personnel = Personnel.objects.get(id=personnel_id, is_deleted=False)
        except Personnel.DoesNotExist:
            raise ValidationError({'personnel': '人员不存在'})

        # 校验职务存在
        try:
            position = Position.objects.get(id=position_id, is_deleted=False)
        except Position.DoesNotExist:
            raise ValidationError({'position': '职务不存在'})

        # 检查是否已有关联
        exists = PersonnelPosition.objects.filter(
            personnel=personnel,
            position=position,
            is_active=True
        ).exists()

        if exists:
            raise ValidationError({'position': '该人员已有此职务'})

        # 检查是否可兼职（一人多职）
        if not position.is_concurrentable:
            current_positions = PersonnelPosition.objects.filter(
                personnel=personnel,
                is_active=True
            ).count()
            if current_positions > 0:
                raise ValidationError({
                    'position': f'{position.name} 不可兼职，当前已有职务'
                })

        # 创建关联
        pp = PersonnelPosition.objects.create(
            personnel=personnel,
            position=position,
            is_primary=is_primary,
            is_active=True
        )
        logger.success(f"[PersonnelService] 职务分配成功: id={pp.id}")
        logger.info(
            f"Position assigned: personnel_id={personnel_id}, position_id={position_id}, is_primary={is_primary}")

        return pp

    @staticmethod
    @transaction.atomic
    def remove_position(personnel_id: int, position_id: int) -> bool:
        """
        移除职务（软删除）

        Args:
            personnel_id: 人员ID
            position_id: 职务ID

        Returns:
            bool: 是否成功
        """
        logger.info(f"[PersonnelService] 移除职务: personnel_id={personnel_id}, position_id={position_id}")

        try:
            pp = PersonnelPosition.objects.get(
                personnel_id=personnel_id,
                position_id=position_id,
                is_active=True
            )
            pp.is_active = False
            pp.save(update_fields=['is_active'])

            logger.success(f"[PersonnelService] 职务移除成功")
            return True

        except PersonnelPosition.DoesNotExist:
            logger.warning(f"[PersonnelService] 关联记录不存在")
            return False

    @staticmethod
    def get_personnel_positions(personnel_id: int) -> list[PersonnelPosition]:
        """
        获取人员的所有有效职务

        Args:
            personnel_id: 人员ID

        Returns:
            list[PersonnelPosition]: 职务列表
        """
        return list(PersonnelPosition.objects.filter(
            personnel_id=personnel_id,
            is_active=True
        ).select_related('position'))

    @staticmethod
    def validate_id_card(id_card: str) -> bool:
        """
        校验身份证号格式

        Args:
            id_card: 身份证号

        Returns:
            bool: 是否合法
        """
        if not id_card:
            return False

        if len(id_card) != 18:
            return False

        # 末位可以是数字或 X
        if not id_card[-1].isdigit() and id_card[-1].upper() != 'X':
            return False

        return True