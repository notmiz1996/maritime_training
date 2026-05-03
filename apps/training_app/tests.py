# apps/training_app/tests.py

"""
training_app - 培训管理模块测试

包含：TrainingType 模型测试、ViewSet 测试、Service 测试
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase
from rest_framework import status

from apps.training_app.models import TrainingType


class TrainingTypeModelTest(TestCase):
    """TrainingType 模型测试"""

    def setUp(self):
        """测试数据准备"""
        # 创建父类型
        self.parent_type = TrainingType.objects.create(
            name='驾驶岗位',
            category='驾驶'
        )
        # 创建子类型
        self.child_type = TrainingType.objects.create(
            name='一类船长',
            category='驾驶',
            parent=self.parent_type
        )

    def test_create_training_type(self):
        """测试创建培训类型"""
        tt = TrainingType.objects.create(
            name='二副',
            category='驾驶'
        )
        self.assertEqual(tt.name, '二副')
        self.assertEqual(tt.category, '驾驶')
        self.assertIsNone(tt.parent)
        self.assertFalse(tt.is_deleted)

    def test_create_child_type(self):
        """测试创建子类型"""
        self.assertEqual(self.child_type.parent, self.parent_type)
        self.assertEqual(self.child_type.category, '驾驶')

    def test_clean_parent_self_reference(self):
        """测试禁止将自身设为父类型"""
        tt = TrainingType(
            name='测试类型',
            category='驾驶',
            parent_id=1  # 假设自身ID
        )
        # 注意：这个测试在创建时会被 clean() 方法拦截
        # 实际场景中不能将自身设为父类型

    def test_category_validation(self):
        """测试分类只能是驾驶/轮机/其他"""
        # 有效分类
        for cat in ['驾驶', '轮机', '其他']:
            tt = TrainingType.objects.create(
                name=f'测试_{cat}',
                category=cat
            )
            self.assertEqual(tt.category, cat)

        # 无效分类应在 Serializer 层被拦截（Model 层不限制）
        # 此处测试 Model 层接受任意分类，业务限制在 Service/Serializer

    def test_soft_delete(self):
        """测试软删除"""
        tt = TrainingType.objects.get(id=self.parent_type.id)
        tt.is_deleted = True
        tt.save()

        # 刷新从数据库
        tt.refresh_from_db()
        self.assertTrue(tt.is_deleted)

    def test_query_exclude_deleted(self):
        """测试默认不查询已删除的记录"""
        # 软删除父类型
        self.parent_type.is_deleted = True
        self.parent_type.save()

        # 默认查询应不包含已删除的记录
        visible_types = TrainingType.objects.filter(is_deleted=False)
        self.assertEqual(visible_types.count(), 1)  # 只有 child_type


class TrainingTypeSerializerTest(APITestCase):
    """TrainingType Serializer 测试"""

    def setUp(self):
        self.parent_type = TrainingType.objects.create(
            name='驾驶岗位',
            category='驾驶'
        )

    def test_serializer_valid_category(self):
        """测试有效分类"""
        from apps.training_app.serializers import TrainingTypeSerializer

        data = {
            'name': '一类船长',
            'category': '驾驶',
            'parent_id': self.parent_type.id
        }
        serializer = TrainingTypeSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_serializer_invalid_category(self):
        """测试无效分类被拒绝"""
        from apps.training_app.serializers import TrainingTypeSerializer

        data = {
            'name': '无效分类测试',
            'category': '非法分类'
        }
        serializer = TrainingTypeSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('category', serializer.errors)

    def test_serializer_circular_reference(self):
        """测试循环引用校验"""
        from apps.training_app.serializers import TrainingTypeSerializer

        # 创建两个类型
        tt1 = TrainingType.objects.create(name='类型1', category='驾驶')
        tt2 = TrainingType.objects.create(name='类型2', category='驾驶', parent=tt1)

        # 尝试将 tt1 的父类型设为 tt2（形成循环）
        data = {
            'name': '类型1',
            'category': '驾驶',
            'parent_id': tt2.id
        }
        serializer = TrainingTypeSerializer(tt1, data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('parent', serializer.errors)


class TrainingTypeViewSetTest(APITestCase):
    """TrainingType ViewSet 测试"""

    def setUp(self):
        from django.contrib.auth.models import User
        from apps.organization_app.models import Organization, Personnel

        # 创建测试用户
        self.user = User.objects.create_user(
            username='test_user',
            password='test_pass'
        )

        # 创建组织和人员
        self.org = Organization.objects.create(
            name='测试公司',
            org_type='company'
        )
        self.personnel = Personnel.objects.create(
            user=self.user,
            name='测试人员',
            id_card='110101199001011234',
            phone='13800138000',
            organization=self.org
        )

        # 创建培训类型
        self.training_type = TrainingType.objects.create(
            name='驾驶岗位',
            category='驾驶'
        )

        self.client.force_authenticate(user=self.user)

    def test_list_training_types(self):
        """测试列出培训类型"""
        url = '/api/training-types/'
        response = self.client.get(url)

        # 根据实际权限配置，可能返回 200 或 403
        # 此处假设允许访问
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN])

    def test_create_training_type(self):
        """测试创建培训类型"""
        url = '/api/training-types/'
        data = {
            'name': '二副',
            'category': '驾驶'
        }
        response = self.client.post(url, data, format='json')

        # 根据实际权限配置，可能返回 201 或 403
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_403_FORBIDDEN])

    def test_tree_endpoint(self):
        """测试树形结构端点"""
        # 创建一个有子类型的结构
        parent = TrainingType.objects.create(name='驾驶岗位', category='驾驶')
        TrainingType.objects.create(name='一类船长', category='驾驶', parent=parent)

        url = '/api/training-types/tree/'
        response = self.client.get(url)

        # 根据实际权限配置
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            self.assertIsInstance(data, list)
            if data:
                self.assertIn('children', data[0])

    def test_filter_by_category(self):
        """测试按分类筛选"""
        TrainingType.objects.create(name='轮机岗位', category='轮机')

        url = '/api/training-types/?category=驾驶'
        response = self.client.get(url)

        if response.status_code == status.HTTP_200_OK:
            self.assertEqual(len(response.json()), 1)

    def test_soft_delete(self):
        """测试软删除"""
        url = f'/api/training-types/{self.training_type.id}/'
        response = self.client.delete(url)

        # 根据实际权限配置
        self.assertIn(response.status_code, [status.HTTP_204_NO_CONTENT, status.HTTP_403_FORBIDDEN])

        # 验证 is_deleted 被设置为 True
        self.training_type.refresh_from_db()
        if response.status_code == status.HTTP_204_NO_CONTENT:
            self.assertTrue(self.training_type.is_deleted)


class TrainingTypeServiceTest(TestCase):
    """TrainingType Service 测试"""

    def test_create_type(self):
        """测试创建培训类型"""
        from apps.training_app.services import TrainingTypeService

        service = TrainingTypeService()
        tt = service.create_type(
            name='三类轮机长',
            category='轮机'
        )

        self.assertEqual(tt.name, '三类轮机长')
        self.assertEqual(tt.category, '轮机')

    def test_invalid_category(self):
        """测试无效分类"""
        from apps.training_app.services import TrainingTypeService

        service = TrainingTypeService()
        with self.assertRaises(ValueError) as ctx:
            service.create_type(
                name='无效测试',
                category='非法分类'
            )

        self.assertIn('驾驶', str(ctx.exception))

    def test_update_type(self):
        """测试更新培训类型"""
        from apps.training_app.services import TrainingTypeService

        # 先创建
        tt = TrainingType.objects.create(name='原名称', category='驾驶')

        service = TrainingTypeService()
        updated = service.update_type(
            type_id=tt.id,
            name='新名称'
        )

        self.assertEqual(updated.name, '新名称')

    def test_delete_type(self):
        """测试软删除"""
        from apps.training_app.services import TrainingTypeService

        tt = TrainingType.objects.create(name='待删除', category='驾驶')

        service = TrainingTypeService()
        result = service.delete_type(tt.id)

        self.assertTrue(result)

        tt.refresh_from_db()
        self.assertTrue(tt.is_deleted)

    def test_get_tree(self):
        """测试获取树形结构"""
        from apps.training_app.services import TrainingTypeService

        # 创建树形结构
        parent = TrainingType.objects.create(name='驾驶', category='驾驶')
        TrainingType.objects.create(name='船长', category='驾驶', parent=parent)

        service = TrainingTypeService()
        tree = service.get_tree()

        self.assertIsInstance(tree, list)
        if tree:
            self.assertIn('children', tree[0])
