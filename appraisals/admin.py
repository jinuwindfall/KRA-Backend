from django.contrib import admin
from .models import Appraisal, KRA


@admin.register(Appraisal)
class AppraisalAdmin(admin.ModelAdmin):
    list_display = ('employee', 'appraisal_type', 'period_from', 'period_to', 'status')
    fieldsets = (
        (None, {'fields': ('employee', 'appraisal_type', 'period_from', 'period_to', 'status')}),
        ('Remarks', {'fields': ('employee_remarks', 'appraiser_remarks', 'reviewer_remarks')}),
        ('Strong & Weak Areas', {'fields': ('strong_areas', 'weak_areas')}),
        ('Training Needs', {'fields': ('training_need_a', 'training_need_b', 'training_need_c')}),
        ('Growth Prospects', {'fields': ('eligible_for_confirmation', 'considered_for_additional_responsibilities')}),
        ('MGMT / HR', {'fields': ('mgmt_hr_remarks',)}),
    )


@admin.register(KRA)
class KRAAdmin(admin.ModelAdmin):
    list_display = ('appraisal', 'section', 'sl_no', 'title', 'max_mark', 'appraisee_mark', 'appraiser_mark', 'reviewer_mark')
    list_filter = ('section',)
    fields = ('appraisal', 'section', 'sl_no', 'title', 'description', 'max_mark')
    readonly_fields = ()
