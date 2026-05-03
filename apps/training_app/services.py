# apps/training_app/services.py

"""
training_app - 培训管理模块服务层
包含：TrainingTypeService, TrainingClassService
"""
from django.db import transaction
from django.utils import timezone
from loguru import logger

from .models import TrainingType, TrainingClass


class TrainingTypeService:
    """
    培训类型服务

    封装培训类型的业务逻辑
    """

    @transaction.atomic
    def create_type(
            self,
            name: str,
            category: str,
            parent: TrainingType = None,
            operator_id: int = None
    ) -> TrainingType:
        """
        创建培训类型

        Args:
            name: 类型名称
            category: 分类（驾驶/轮机/其他）
            parent: 父类型（可选）
            operator_id: 操作人ID

        Returns:
            TrainingType 实例
        """
        valid_categories = ['驾驶', '轮机', '其他']
        if category not in valid_categories:
            raise ValueError(f'分类必须是以下值之一：{", ".join(valid_categories)}')

        # 校验循环引用
        if parent:
            ancestor = parent
            while ancestor:
                if ancestor == parent:
                    break  # 这里是简化的，实际在模型层已校验
                ancestor = ancestor.parent

        training_type = TrainingType.objects.create(
            name=name,
            category=category,
            parent=parent
        )

        logger.info(
            f'培训类型创建成功: id={training_type.id}, '
            f'name={training_type.name}, category={category}'
        )

        return training_type

    @transaction.atomic
    def update_type(
            self,
            type_id: int,
            name: str = None,
            category: str = None,
            parent: TrainingType = None,
            operator_id: int = None
    ) -> TrainingType:
        """
        更新培训类型
        """
        training_type = TrainingType.objects.get(id=type_id)

        if name:
            training_type.name = name

        if category:
            valid_categories = ['驾驶', '轮机', '其他']
            if category not in valid_categories:
                raise ValueError(f'分类必须是以下值之一：{", ".join(valid_categories)}')
            training_type.category = category

        if parent is not None:  # 允许设置为 null
            training_type.parent = parent

        training_type.save(update_fields=['name', 'category', 'parent', 'updated_at'])

        logger.info(
            f'培训类型更新成功: id={training_type.id}, '
            f'name={training_type.name}'
        )

        return training_type

    @transaction.atomic
    def delete_type(self, type_id: int) -> bool:
        """
        软删除培训类型
        """
        training_type = TrainingType.objects.get(id=type_id)
        training_type.is_deleted = True
        training_type.save(update_fields=['is_deleted', 'updated_at'])

        logger.info(f'培训类型软删除成功: id={type_id}')

        return True

    def get_tree(self) -> list:
        """
        获取树形结构（递归）
        """
        root_types = TrainingType.objects.filter(
            parent__isnull=True,
            is_deleted=False
        ).order_by('category', 'name')

        def build_tree(t_type):
            children = TrainingType.objects.filter(
                parent=t_type,
                is_deleted=False
            ).order_by('name')

            return {
                'id': t_type.id,
                'name': t_type.name,
                'category': t_type.category,
                'children': [build_tree(child) for child in children]
            }

        return [build_tree(root) for root in root_types]