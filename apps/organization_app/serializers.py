# -*- coding: utf-8 -*-
"""
organization_app - Serializer 层
"""

from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Organization, Personnel, Position, PersonnelPosition


class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = [
            'id', 'name', 'org_type', 'parent',
            'level', 'path', 'is_deleted',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'level', 'path', 'created_at', 'updated_at']

    def validate(self, attrs):
        parent = attrs.get('parent')
        if parent:
            if parent.id == self.instance.id if self.instance else None:
                raise serializers.ValidationError({
                    'parent': '不能将自身设为上级组织'
                })
        return attrs


class OrganizationTreeSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ['id', 'name', 'org_type', 'level', 'children']

    def get_children(self, obj):
        children = obj.children.filter(is_deleted=False)
        return OrganizationTreeSerializer(children, many=True).data


# class PersonnelSerializer(serializers.ModelSerializer):
#     organization_name = serializers.CharField(source='organization.name', read_only=True)
#     positions = serializers.SerializerMethodField()
#     user_username = serializers.CharField(source='user.username', read_only=True)
#
#     user = serializers.PrimaryKeyRelatedField(read_only=True)
class PersonnelSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    positions = serializers.SerializerMethodField()
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Personnel
        fields = [
            'id', 'name', 'id_card', 'phone',
            'organization', 'organization_name',
            'user_username',  # 删除 user，只保留显示用
            'positions', 'is_deleted',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'user_username']

    def validate_id_card(self, value):
        if value:
            if len(value) != 18:
                raise serializers.ValidationError('身份证号必须为18位')
            if not value[-1].isdigit() and value[-1].upper() != 'X':
                raise serializers.ValidationError('身份证号格式不正确')
        return value

    def get_positions(self, obj):
        personnel_positions = obj.personnelposition_set.filter(is_active=True)
        return PersonnelPositionSerializer(personnel_positions, many=True).data

    # def create(self, validated_data):
    #     user_id = validated_data.pop('user_id', None)
    #     if user_id:
    #         try:
    #             user = User.objects.get(id=user_id)
    #             validated_data['user'] = user
    #         except User.DoesNotExist:
    #             raise serializers.ValidationError({'user_id': '用户不存在'})
    #     return super().create(validated_data)
    def create(self, validated_data):
        # 强制使用当前请求用户，覆盖请求 body 中的 user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class PersonnelListSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Personnel
        fields = ['id', 'name', 'phone', 'organization_name', 'is_deleted', 'created_at']


class PositionSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(source='organization.name', read_only=True)

    class Meta:
        model = Position
        fields = [
            'id', 'name', 'code', 'organization', 'organization_name',
            'permissions', 'is_concurrentable', 'is_deleted',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_permissions(self, value):
        # ManyToManyField 不需要校验格式，由 Django 处理
        return value


class PersonnelPositionSerializer(serializers.ModelSerializer):
    position_name = serializers.CharField(source='position.name', read_only=True)
    position_code = serializers.CharField(source='position.code', read_only=True)
    personnel_name = serializers.CharField(source='personnel.name', read_only=True)

    class Meta:
        model = PersonnelPosition
        fields = [
            'id', 'personnel', 'personnel_name',
            'position', 'position_name', 'position_code',
            'is_primary', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AssignPositionSerializer(serializers.Serializer):
    position_id = serializers.IntegerField(required=True)
    is_primary = serializers.BooleanField(default=False)
