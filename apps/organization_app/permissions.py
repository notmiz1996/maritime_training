# -*- coding: utf-8 -*-
"""
organization_app - Permission 层

职责：
- 自定义权限类
- 实现矩阵式权限控制（基于 Position.permissions）
"""

from rest_framework.permissions import BasePermission

from loguru import logger

from .models import Personnel, PersonnelPosition


class MatrixPermission(BasePermission):
    """
    矩阵式权限类

    基于 Position.permissions（ManyToMany）的权限控制

    使用方式：
    class MyViewSet(ViewSet):
        permission_classes = [IsAuthenticated, MatrixPermission]
        required_permissions = ['training.view', 'training.approve']

    权限检查流程：
    1. 获取当前用户的 Personnel
    2. 获取该 Personnel 的所有 Position
    3. 合并所有 Position 的 permissions
    4. 检查是否包含 required_permissions 中的所有权限
    """

    message = '您没有足够的权限执行此操作'

    def has_permission(self, request, view):
        """检查用户是否有权限访问此 ViewSet"""
        user = request.user

        if not user or not user.is_authenticated:
            logger.warning(f"[MatrixPermission] 用户未登录")
            return False

        required_permissions = getattr(view, 'required_permissions', [])

        if not required_permissions:
            return True

        user_permissions = self._get_user_permissions(user)

        has_permission = all(perm in user_permissions for perm in required_permissions)

        if not has_permission:
            missing = [p for p in required_permissions if p not in user_permissions]
            logger.warning(
                f"[MatrixPermission] 权限不足: user={user.id}, missing={missing}"
            )

        return has_permission

    def has_object_permission(self, request, view, obj):
        """检查用户是否有权限操作此对象"""
        return self.has_permission(request, view)

    @staticmethod
    def _get_user_permissions(user) -> set[str]:
        """
        获取用户的完整权限集合

        权限来源：
        1. User.user_permissions（ Django 内置）
        2. Personnel → PersonnelPosition → Position.permissions（ManyToMany）

        Returns:
            set[str]: 权限集合，如 {'training.view', 'training.approve'}
        """
        permissions = set()

        # 1. 获取 Django User 的权限
        if hasattr(user, 'user_permissions'):
            user_perms = user.user_permissions.values_list('codename', flat=True)
            permissions.update(user_perms)

        # 如果是 superuser，拥有所有权限
        if user.is_superuser:
            logger.debug(f"[MatrixPermission] superuser 拥有所有权限")
            return permissions

        # 2. 获取 Personnel 的权限
        try:
            personnel = Personnel.objects.get(user=user, is_deleted=False)
        except Personnel.DoesNotExist:
            logger.debug(f"[MatrixPermission] 用户无 Personnel 记录: user={user.id}")
            return permissions

        # 3. 获取所有有效的 PersonnelPosition
        personnel_positions = PersonnelPosition.objects.filter(
            personnel=personnel,
            is_active=True
        ).select_related('position')

        # 4. 合并所有 Position 的 permissions（ManyToMany → list）
        # 【关键修复】return 必须在 for 循环之外
        for pp in personnel_positions:
            position_perms = list(
                pp.position.permissions.values_list('codename', flat=True)
            )
            permissions.update(position_perms)

            if pp.is_primary:
                logger.debug(
                    f"[MatrixPermission] 主职务权限: "
                    f"{pp.position.name} -> {position_perms}"
                )

        logger.debug(f"[MatrixPermission] 用户权限集合: {permissions}")
        return permissions  # ✅ 正确：在循环之外


class ObjectPermission(BasePermission):
    """
    对象级权限

    用于检查用户是否有权限操作特定对象
    例如：只能操作自己创建的资源
    """

    message = '您没有权限操作此对象'

    def has_object_permission(self, request, view, obj):
        """检查用户是否有权限操作此对象"""
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if hasattr(obj, 'created_by'):
            return obj.created_by == user

        if hasattr(obj, 'created_by_id'):
            return obj.created_by_id == user.id

        return True


# ========== 权限辅助函数（模块级函数，非类方法）==========

def get_user_permissions(user) -> set[str]:
    """获取用户权限集合"""
    return MatrixPermission._get_user_permissions(user)


def has_permission(user, permission: str) -> bool:
    """检查用户是否拥有特定权限"""
    return permission in get_user_permissions(user)


def has_any_permission(user, permissions: list[str]) -> bool:
    """检查用户是否拥有任意一个权限"""
    user_perms = get_user_permissions(user)
    return any(p in user_perms for p in permissions)


def has_all_permissions(user, permissions: list[str]) -> bool:
    """检查用户是否拥有所有指定权限"""
    user_perms = get_user_permissions(user)
    return all(p in user_perms for p in permissions)