# -*- coding: utf-8 -*-
"""
organization_app - 测试（完整修复版）
"""

from django.test import TestCase
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status

from .models import Organization, Personnel, Position, PersonnelPosition
from .services import OrganizationService, PersonnelService
from .permissions import get_user_permissions, has_permission, has_all_permissions


# =============================================================================
# Model 层测试
# =============================================================================

class OrganizationModelTest(TestCase):
    """Organization 模型测试"""

    def setUp(self):
        self.company = Organization.objects.create(
            name='测试公司', org_type='company',
        )

    def test_create_organization(self):
        """测试创建组织"""
        org = Organization.objects.create(
            name='测试部门', org_type='department', parent=self.company,
        )
        self.assertEqual(org.name, '测试部门')

    def test_soft_delete(self):
        """软删除后查询应该排除"""
        org = Organization.objects.create(name='待删除', org_type='department')
        org.is_deleted = True
        org.save()
        result = Organization.objects.filter(id=org.id, is_deleted=False).first()
        self.assertIsNone(result)

    def test_get_children(self):
        """测试获取子组织"""
        child = Organization.objects.create(
            name='子部门', org_type='department', parent=self.company,
        )
        children = self.company.children.all()
        self.assertEqual(children.count(), 1)


class PersonnelModelTest(TestCase):
    """Personnel 模型测试"""

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.org = Organization.objects.create(name='测试组织', org_type='company')

    def test_create_personnel(self):
        """user 必填"""
        personnel = Personnel.objects.create(
            name='张三', id_card='110101199001011234',
            phone='13800138000', organization=self.org, user=self.user,
        )
        self.assertEqual(personnel.name, '张三')

    def test_soft_delete(self):
        """软删除测试"""
        personnel = Personnel.objects.create(
            name='李四', id_card='110101199001011235',
            phone='13800138001', organization=self.org, user=self.user,
        )
        personnel.is_deleted = True
        personnel.save()
        result = Personnel.objects.filter(id=personnel.id, is_deleted=False).first()
        self.assertIsNone(result)


class PositionModelTest(TestCase):
    """Position 模型测试"""

    def setUp(self):
        self.org = Organization.objects.create(name='测试组织', org_type='company')

    def test_create_position(self):
        """测试创建职务（无 level 字段）"""
        position = Position.objects.create(
            code='CEO', name='首席执行官', organization=self.org,
        )
        self.assertEqual(position.code, 'CEO')

    def test_permissions_mtm(self):
        """测试 ManyToMany 权限关联"""
        position = Position.objects.create(
            code='ADMIN', name='管理员', organization=self.org,
        )
        content_type = ContentType.objects.get_for_model(Organization)
        perm = Permission.objects.create(
            codename='manage_org', name='管理组织', content_type=content_type,
        )
        position.permissions.add(perm)
        self.assertEqual(position.permissions.count(), 1)


class PersonnelPositionModelTest(TestCase):
    """PersonnelPosition 模型测试"""

    def setUp(self):
        self.org = Organization.objects.create(name='测试组织', org_type='company')
        self.user = User.objects.create_user(username='testuser2', password='testpass123')
        self.personnel = Personnel.objects.create(
            name='王五', id_card='110101199001011236',
            phone='13800138002', organization=self.org, user=self.user,
        )
        self.position = Position.objects.create(
            code='MGR', name='经理', organization=self.org,
        )

    def test_assign_position(self):
        """测试分配职务"""
        pp = PersonnelPosition.objects.create(
            personnel=self.personnel, position=self.position,
            is_primary=True, is_active=True,
        )
        self.assertTrue(pp.is_primary)

    def test_remove_position(self):
        """测试移除职务（软删除）"""
        pp = PersonnelPosition.objects.create(
            personnel=self.personnel, position=self.position, is_active=True,
        )
        pp.is_active = False
        pp.save()
        active_pp = PersonnelPosition.objects.filter(
            personnel=self.personnel, position=self.position, is_active=True
        ).first()
        self.assertIsNone(active_pp)


# =============================================================================
# Service 层测试
# =============================================================================

class OrganizationServiceTest(TestCase):
    """OrganizationService 测试"""

    def setUp(self):
        self.company = Organization.objects.create(name='总公司', org_type='company')

    def test_create_organization(self):
        """测试创建组织"""
        org = OrganizationService.create_organization(
            name='测试部门', org_type='department', parent_id=self.company.id,
        )
        self.assertEqual(org.level, 1)

    def test_create_organization_exceed_level_10(self):
        """测试层级超限"""
        parent = self.company
        for i in range(10):
            parent = Organization.objects.create(
                name=f'第{i}级', org_type='department', parent=parent,
            )
        with self.assertRaises(ValidationError):
            OrganizationService.create_organization(
                name='超限', org_type='department', parent_id=parent.id,
            )

    def test_get_subtree(self):
        """测试获取子树"""
        child = Organization.objects.create(
            name='子部门', org_type='department', parent=self.company,
        )
        subtree = OrganizationService.get_subtree(self.company.id)
        self.assertEqual(len(subtree), 1)

    def test_soft_delete(self):
        """软删除测试（需要 services.py soft_delete 有 org.save()）"""
        org = Organization.objects.create(
            name='待删除', org_type='department', parent=self.company,
        )
        result = OrganizationService.soft_delete(org.id)
        self.assertTrue(result)
        org.refresh_from_db()
        self.assertTrue(org.is_deleted)


class PersonnelServiceTest(TestCase):
    """
    PersonnelService 测试
    所有 Personnel 创建必须带 user=
    """

    def setUp(self):
        self.org = Organization.objects.create(name='测试公司', org_type='company')
        self.user = User.objects.create_user(username='svc_user', password='testpass123')
        self.position = Position.objects.create(
            code='MGR', name='经理', organization=self.org,
        )

    def test_create_personnel(self):
        """测试创建人员（user_id 必填）"""
        personnel = PersonnelService.create_personnel(
            name='张三', id_card='110101199001011234',
            phone='13800138000', organization_id=self.org.id,
            user_id=self.user.id,
        )
        self.assertEqual(personnel.name, '张三')

    def test_create_personnel_invalid_id_card(self):
        """测试身份证号无效"""
        with self.assertRaises(ValidationError):
            PersonnelService.create_personnel(
                name='张三', id_card='123',
                phone='13800138000', organization_id=self.org.id,
            )

    def test_assign_position(self):
        """测试分配职务（Personnel 创建带 user=）"""
        personnel = Personnel.objects.create(
            name='李四', id_card='110101199001011235',
            phone='13800138001', organization=self.org,
            user=self.user,
        )
        pp = PersonnelService.assign_position(
            personnel_id=personnel.id, position_id=self.position.id, is_primary=True,
        )
        self.assertEqual(pp.position, self.position)

    def test_assign_position_duplicate(self):
        """测试重复分配职务"""
        personnel = Personnel.objects.create(
            name='王五', id_card='110101199001011236',
            phone='13800138002', organization=self.org,
            user=self.user,
        )
        PersonnelService.assign_position(
            personnel_id=personnel.id, position_id=self.position.id,
        )
        with self.assertRaises(ValidationError):
            PersonnelService.assign_position(
                personnel_id=personnel.id, position_id=self.position.id,
            )

    def test_assign_position_not_concurrentable(self):
        """测试不可兼职职务"""
        pos2 = Position.objects.create(
            code='CEO', name='首席执行官', organization=self.org, is_concurrentable=False,
        )
        personnel = Personnel.objects.create(
            name='赵六', id_card='110101199001011237',
            phone='13800138003', organization=self.org,
            user=self.user,
        )
        PersonnelService.assign_position(
            personnel_id=personnel.id, position_id=self.position.id,
        )
        with self.assertRaises(ValidationError):
            PersonnelService.assign_position(
                personnel_id=personnel.id, position_id=pos2.id,
            )

    def test_remove_position(self):
        """测试移除职务"""
        personnel = Personnel.objects.create(
            name='孙七', id_card='110101199001011238',
            phone='13800138004', organization=self.org,
            user=self.user,
        )
        PersonnelService.assign_position(
            personnel_id=personnel.id, position_id=self.position.id,
        )
        result = PersonnelService.remove_position(
            personnel_id=personnel.id, position_id=self.position.id,
        )
        self.assertTrue(result)


# =============================================================================
# View 层测试（API 测试）
# =============================================================================

class OrganizationViewSetTest(TestCase):
    """OrganizationViewSet API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.company = Organization.objects.create(name='总公司', org_type='company')

    def test_list(self):
        """测试列出组织"""
        response = self.client.get('/api/organizations/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        """测试创建组织"""
        response = self.client.post('/api/organizations/', {
            'name': '新部门', 'org_type': 'department',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve(self):
        """测试获取单个组织"""
        response = self.client.get(f'/api/organizations/{self.company.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_soft_delete(self):
        """软删除测试"""
        org = Organization.objects.create(
            name='待删除', org_type='department', parent=self.company,
        )
        response = self.client.delete(f'/api/organizations/{org.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        org.refresh_from_db()
        self.assertTrue(org.is_deleted)

    def test_tree(self):
        """测试获取树形结构"""
        response = self.client.get('/api/organizations/tree/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_descendants(self):
        """测试获取后代"""
        Organization.objects.create(
            name='子部门', org_type='department', parent=self.company,
        )
        response = self.client.get(f'/api/organizations/{self.company.id}/descendants/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_children(self):
        """测试获取直接子节点"""
        Organization.objects.create(
            name='子部门', org_type='department', parent=self.company,
        )
        response = self.client.get(f'/api/organizations/{self.company.id}/children/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PersonnelViewSetTest(TestCase):
    """PersonnelViewSet API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser2', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.org = Organization.objects.create(name='测试公司', org_type='company')
        self.personnel = Personnel.objects.create(
            name='张三', id_card='110101199001011234',
            phone='13800138000', organization=self.org, user=self.user,
        )

    def test_list(self):
        """测试列出人员"""
        response = self.client.get('/api/personnels/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        """测试创建人员"""
        # 【关键】创建一个全新的用户来测试 API 创建
        new_user = User.objects.create_user(
            username='test_api_create_user',
            password='testpass123'
        )
        self.client.force_authenticate(user=new_user)  # 用新用户认证

        response = self.client.post('/api/personnels/', {
            'name': '李四',
            'id_card': '110101199001011235',
            'phone': '13800138001',
            'organization': self.org.id,
            # 不传 user 字段，view 层会用 request.user
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # user = User.objects.create_user(
        #     username='test_create_personnel_api',
        #     password='testpass123'
        # )
        #
        # response = self.client.post('/api/personnels/', {
        #     'name': '李四',
        #     'id_card': '110101199001011235',
        #     'phone': '13800138001',
        #     'organization': self.org.id,
        #     'user': user.id,
        # })
        # self.assertEqual(response.status_code, 201)
        # self.assertEqual(response.data['name'], '李四')

    def test_retrieve(self):
        """测试获取单个人员"""
        response = self.client.get(f'/api/personnels/{self.personnel.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_assign_position(self):
        """测试分配职务"""
        position = Position.objects.create(
            code='MGR', name='经理', organization=self.org,
        )
        response = self.client.post(
            f'/api/personnels/{self.personnel.id}/assign-position/',
            {'position_id': position.id, 'is_primary': True}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_remove_position(self):
        """测试移除职务"""
        position = Position.objects.create(
            code='MGR', name='经理', organization=self.org,
        )
        PersonnelPosition.objects.create(
            personnel=self.personnel, position=position, is_active=True,
        )
        response = self.client.delete(
            f'/api/personnels/{self.personnel.id}/remove-position/?position_id={position.id}'
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_get_positions(self):
        """测试获取人员职务列表"""
        response = self.client.get(f'/api/personnels/{self.personnel.id}/positions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PositionViewSetTest(TestCase):
    """PositionViewSet API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser3', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.org = Organization.objects.create(name='测试公司', org_type='company')

    def test_list(self):
        """测试列出职务"""
        response = self.client.get('/api/positions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        """测试创建职务"""
        response = self.client.post('/api/positions/', {
            'code': 'CEO', 'name': '首席执行官', 'organization': self.org.id,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_retrieve(self):
        """测试获取单个职务"""
        position = Position.objects.create(
            code='MGR', name='经理', organization=self.org,
        )
        response = self.client.get(f'/api/positions/{position.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class PersonnelPositionViewSetTest(TestCase):
    """PersonnelPositionViewSet API 测试"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser4', password='testpass123')
        self.client.force_authenticate(user=self.user)
        self.org = Organization.objects.create(name='测试公司', org_type='company')
        self.personnel = Personnel.objects.create(
            name='张三', id_card='110101199001011234',
            phone='13800138000', organization=self.org, user=self.user,
        )
        self.position = Position.objects.create(
            code='MGR', name='经理', organization=self.org,
        )

    def test_list(self):
        """测试列出关联"""
        response = self.client.get('/api/personnel-positions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create(self):
        """测试创建关联"""
        response = self.client.post('/api/personnel-positions/', {
            'personnel': self.personnel.id,
            'position': self.position.id,
            'is_primary': True,
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


# =============================================================================
# Permission 层测试
# =============================================================================

class MatrixPermissionTest(TestCase):
    """MatrixPermission 测试"""

    def setUp(self):
        self.org = Organization.objects.create(name='测试公司', org_type='company')

        content_type = ContentType.objects.get_for_model(Organization)
        self.perm_view = Permission.objects.create(
            codename='view_org', name='查看组织', content_type=content_type,
        )
        self.perm_manage = Permission.objects.create(
            codename='manage_org', name='管理组织', content_type=content_type,
        )

        self.position = Position.objects.create(
            code='ADMIN', name='管理员', organization=self.org,
        )
        self.position.permissions.add(self.perm_view, self.perm_manage)

        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.personnel = Personnel.objects.create(
            name='张三', id_card='110101199001011234',
            phone='13800138000', organization=self.org, user=self.user,
        )
        PersonnelPosition.objects.create(
            personnel=self.personnel, position=self.position,
            is_primary=True, is_active=True,
        )

    def test_get_user_permissions(self):
        """测试获取用户权限集合"""
        perms = get_user_permissions(self.user)
        self.assertIn('view_org', perms)
        self.assertIn('manage_org', perms)

    def test_has_permission(self):
        """测试单个权限检查"""
        self.assertTrue(has_permission(self.user, 'view_org'))
        self.assertFalse(has_permission(self.user, 'nonexistent'))

    def test_has_all_permissions(self):
        """测试是否拥有所有权限（AND 逻辑）"""
        self.assertTrue(has_all_permissions(self.user, ['view_org', 'manage_org']))
        self.assertFalse(has_all_permissions(self.user, ['view_org', 'nonexistent']))

    def test_no_personnel(self):
        """测试用户无 Personnel 记录"""
        user2 = User.objects.create_user(username='testuser2', password='testpass123')
        perms = get_user_permissions(user2)
        self.assertEqual(len(perms), 0)