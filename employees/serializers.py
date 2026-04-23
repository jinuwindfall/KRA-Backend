from datetime import date

from django.contrib.auth.models import User
from django.utils.text import slugify
from rest_framework import serializers
from appraisals.models import Appraisal
from .models import Department, Employee


def generate_unique_username(name, emp_id):
    # Use full name as username (e.g. "Jinu Thomas")
    candidate = (name or '').strip() or str(emp_id)
    if not User.objects.filter(username=candidate).exists():
        return candidate
    # Conflict: append emp_id to ensure uniqueness
    return f"{candidate}_{emp_id}"
    return candidate


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name']


class EmployeeListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    department_name = serializers.SerializerMethodField()
    appraiser_name = serializers.SerializerMethodField()
    reviewer_name = serializers.SerializerMethodField()
    reviewer_departments = DepartmentSerializer(many=True, read_only=True)
    appraiser_departments = DepartmentSerializer(many=True, read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'emp_id', 'name', 'first_name', 'last_name', 'department', 'department_name',
            'designation', 'role', 'date_of_joining', 'is_active', 'gender',
            'appraiser', 'appraiser_name', 'reviewer', 'reviewer_name',
            'reviewer_departments', 'appraiser_departments',
        ]

    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def get_department_name(self, obj):
        return obj.department.name if obj.department else 'Unassigned Department'

    def get_appraiser_name(self, obj):
        return obj.appraiser.user.get_full_name() if obj.appraiser else ''

    def get_reviewer_name(self, obj):
        return obj.reviewer.user.get_full_name() if obj.reviewer else ''


class EmployeeCreateSerializer(serializers.Serializer):
    # User account fields (username/password are auto-generated)
    name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    username = serializers.CharField(max_length=150, required=False, allow_blank=True)
    first_name = serializers.CharField(max_length=150, default='', required=False)
    last_name = serializers.CharField(max_length=150, default='', required=False)
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=1, required=False, allow_blank=True)

    # Employee profile fields
    emp_id = serializers.CharField(max_length=20)
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), required=False, allow_null=True
    )
    designation = serializers.CharField(max_length=100)
    role = serializers.ChoiceField(choices=Employee.ROLE_CHOICES)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False)
    gender = serializers.ChoiceField(
        choices=Employee.GENDER_CHOICES, required=False, allow_null=True, allow_blank=True
    )
    appraiser = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), required=False, allow_null=True
    )
    reviewer = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.all(), required=False, allow_null=True
    )
    reviewer_departments = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), many=True, required=False
    )
    appraiser_departments = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), many=True, required=False
    )

    def validate_emp_id(self, value):
        queryset = Employee.objects.filter(emp_id=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise serializers.ValidationError('An employee with this ID already exists.')
        return value

    def create(self, validated_data):
        reviewer_depts = validated_data.pop('reviewer_departments', [])
        appraiser_depts = validated_data.pop('appraiser_departments', [])

        raw_name = (validated_data.pop('name', '') or '').strip()
        username_hint = (validated_data.pop('username', '') or '').strip()
        validated_data.pop('password', None)

        first_name = (validated_data.pop('first_name', '') or '').strip()
        last_name = (validated_data.pop('last_name', '') or '').strip()
        email = (validated_data.pop('email', '') or '').strip()

        if raw_name and not (first_name or last_name):
            name_parts = raw_name.split(maxsplit=1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

        display_name = raw_name or f"{first_name} {last_name}".strip() or username_hint or str(validated_data['emp_id'])
        username = generate_unique_username(display_name, validated_data['emp_id'])

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            # Password must match employee ID by business rule.
            password=str(validated_data['emp_id']),
        )
        employee = Employee.objects.create(user=user, **validated_data)
        if reviewer_depts:
            employee.reviewer_departments.set(reviewer_depts)
        if appraiser_depts:
            employee.appraiser_departments.set(appraiser_depts)

        today = date.today()
        period_from = date(today.year, 1, 1)
        period_to = date(today.year, 12, 31)
        Appraisal.objects.get_or_create(
            employee=employee,
            appraisal_type='Annual',
            period_from=period_from,
            period_to=period_to,
            defaults={'status': Appraisal.STATUS_DRAFT},
        )
        return employee

    def update(self, instance, validated_data):
        reviewer_depts = validated_data.pop('reviewer_departments', None)
        appraiser_depts = validated_data.pop('appraiser_departments', None)

        raw_name = validated_data.pop('name', None)
        validated_data.pop('username', None)
        validated_data.pop('password', None)

        first_name = validated_data.pop('first_name', None)
        last_name = validated_data.pop('last_name', None)
        email = validated_data.pop('email', None)

        if raw_name is not None and not (first_name or last_name):
            name_parts = raw_name.strip().split(maxsplit=1)
            first_name = name_parts[0] if name_parts else ''
            last_name = name_parts[1] if len(name_parts) > 1 else ''

        user = instance.user
        if first_name is not None:
            user.first_name = first_name.strip()
        if last_name is not None:
            user.last_name = last_name.strip()
        if email is not None:
            user.email = email.strip()
        user.save(update_fields=['first_name', 'last_name', 'email'])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if reviewer_depts is not None:
            instance.reviewer_departments.set(reviewer_depts)
        if appraiser_depts is not None:
            instance.appraiser_departments.set(appraiser_depts)

        return instance
