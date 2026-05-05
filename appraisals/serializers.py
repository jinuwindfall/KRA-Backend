from rest_framework import serializers
from .models import Appraisal, KRA, KRATemplate, KRATemplateRow


class AppraisalDisplayMixin:
    """Adds employee context fields needed by frontend employee-info step."""

    def to_representation(self, obj):
        data = super().to_representation(obj)
        emp = obj.employee
        data['employee_emp_id'] = emp.emp_id
        data['employee_designation'] = emp.designation
        data['employee_department'] = emp.department.name if emp.department else 'Unassigned Department'
        data['appraiser_name'] = emp.appraiser.user.get_full_name() if emp.appraiser else ''
        data['reviewer_name'] = emp.reviewer.user.get_full_name() if emp.reviewer else ''
        return data


class KRASerializer(serializers.ModelSerializer):
    """Full access serializer for appraiser/reviewer/hr."""
    class Meta:
        model = KRA
        fields = '__all__'


class KRASerializerHideAppraisee(serializers.ModelSerializer):
    """Hides appraisee_mark until employee has submitted (used by appraiser before Submitted status)."""
    appraisee_mark = serializers.SerializerMethodField()

    class Meta:
        model = KRA
        fields = '__all__'

    def get_appraisee_mark(self, obj):
        # Only expose after employee has submitted
        from .models import Appraisal
        if obj.appraisal.status in (
            Appraisal.STATUS_SUBMITTED,
            Appraisal.STATUS_APPRAISER_REVIEWED,
            Appraisal.STATUS_REVIEWED,
        ):
            return obj.appraisee_mark
        return None


class StaffKRASerializer(serializers.ModelSerializer):
    """Staff can see objective details but only write appraisee_mark."""
    class Meta:
        model = KRA
        fields = [
            'id', 'appraisal', 'section', 'sl_no',
            'title', 'description', 'max_mark',
            'appraisee_mark', 'appraiser_mark', 'reviewer_mark',
        ]
        read_only_fields = [
            'id', 'appraisal', 'section', 'sl_no',
            'title', 'description', 'max_mark',
            'appraiser_mark', 'reviewer_mark',
        ]


class AppraisalSerializer(AppraisalDisplayMixin, serializers.ModelSerializer):
    """Full access for appraiser/reviewer."""
    kras = KRASerializer(many=True, read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Appraisal
        fields = '__all__'

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username


class AppraiserAppraisalSerializer(AppraisalDisplayMixin, serializers.ModelSerializer):
    """Appraiser can write their remarks, strong/weak areas, training, growth."""
    kras = KRASerializerHideAppraisee(many=True, read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Appraisal
        fields = '__all__'
        read_only_fields = [
            'id', 'employee', 'appraisal_type', 'period_from', 'period_to',
            'created_at', 'updated_at',
            'mark_entry_access_open', 'frame_config',
            'employee_remarks', 'reviewer_remarks', 'mgmt_hr_remarks',
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username


class ReviewerAppraisalSerializer(AppraisalDisplayMixin, serializers.ModelSerializer):
    """Reviewer can write reviewer_remarks and mgmt_hr_remarks."""
    kras = KRASerializer(many=True, read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Appraisal
        fields = '__all__'
        read_only_fields = [
            'id', 'employee', 'appraisal_type', 'period_from', 'period_to',
            'created_at', 'updated_at',
            'mark_entry_access_open', 'frame_config', 'extra_appraiser_data',
            'employee_remarks', 'appraiser_remarks',
            'strong_areas', 'weak_areas',
            'training_need_a', 'training_need_b', 'training_need_c',
            'eligible_for_confirmation', 'considered_for_additional_responsibilities',
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username


class HRAppraisalSerializer(AppraisalDisplayMixin, serializers.ModelSerializer):
    """HR has full read/write access to everything."""
    kras = KRASerializer(many=True, read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Appraisal
        fields = '__all__'

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username


class StaffAppraisalSerializer(AppraisalDisplayMixin, serializers.ModelSerializer):
    """Staff can only write employee_remarks and status."""
    kras = StaffKRASerializer(many=True, read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = Appraisal
        fields = '__all__'
        read_only_fields = [
            'id', 'employee', 'appraisal_type', 'period_from', 'period_to',
            'created_at', 'updated_at',
            'mark_entry_access_open', 'frame_config', 'extra_appraiser_data',
            'appraiser_remarks', 'reviewer_remarks',
            'strong_areas', 'weak_areas',
            'training_need_a', 'training_need_b', 'training_need_c',
            'eligible_for_confirmation', 'considered_for_additional_responsibilities',
            'mgmt_hr_remarks',
        ]

    def get_employee_name(self, obj):
        return obj.employee.user.get_full_name() or obj.employee.user.username


class KRATemplateRowSerializer(serializers.ModelSerializer):
    class Meta:
        model = KRATemplateRow
        fields = ['id', 'section', 'sl_no', 'max_mark']


class KRATemplateSerializer(serializers.ModelSerializer):
    rows = KRATemplateRowSerializer(many=True, read_only=True)

    class Meta:
        model = KRATemplate
        fields = ['id', 'frame_config', 'rows', 'period_from', 'period_to', 'updated_at']
