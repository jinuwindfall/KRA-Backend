from django.db import models
from employees.models import Employee


def default_frame_config():
    return {
        'steps': {
            'kra_objectives': True,
            'competencies': True,
            'behaviour': True,
            'appraiser_details': True,
            'remarks': True,
            'performance_ratings': True,
        },
        'appraiser_fields': {
            'strong_areas': True,
            'weak_areas': True,
            'training_need_a': True,
            'training_need_b': True,
            'training_need_c': True,
            'eligible_for_confirmation': True,
            'considered_for_additional_responsibilities': True,
        },
        'step_weights': {
            'kra_objectives': 60,
            'competencies': 20,
            'behaviour': 20,
        },
        'rating_settings': {
            'formula_mode': 'custom_formula',
            'formula_expression': '((appraisee * 20) + (appraiser * 40) + (reviewer * 40)) / 100',
            'formula_weights': {
                'appraisee': 20,
                'appraiser': 40,
                'reviewer': 40,
            },
            'memo_penalty': 0,
            'bands': [
                {'min': 91, 'label': 'Exceeds Expectations'},
                {'min': 81, 'label': 'Perfectly Meets Expectations'},
                {'min': 66, 'label': 'Fairly Meets Expectations'},
                {'min': 51, 'label': 'Somewhat Meets Expectations (PIP)'},
                {'min': 0, 'label': 'Not Meeting Expectations'},
            ],
        },
        'custom_fields': [],
    }


class Appraisal(models.Model):
    STATUS_DRAFT = 'Draft'
    STATUS_SUBMITTED = 'Submitted'
    STATUS_APPRAISER_REVIEWED = 'Appraiser Reviewed'
    STATUS_REVIEWED = 'Reviewed'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_APPRAISER_REVIEWED, 'Appraiser Reviewed'),
        (STATUS_REVIEWED, 'Reviewed'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    appraisal_type = models.CharField(max_length=50, default="Annual")
    period_from = models.DateField()
    period_to = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    mark_entry_access_open = models.BooleanField(default=False)
    frame_config = models.JSONField(default=default_frame_config, blank=True)

    # Remarks
    employee_remarks = models.TextField(blank=True, default='')
    appraiser_remarks = models.TextField(blank=True, default='')
    reviewer_remarks = models.TextField(blank=True, default='')

    # Strong & Weak Areas (appraiser fills)
    strong_areas = models.TextField(blank=True, default='')
    weak_areas = models.TextField(blank=True, default='')

    # Training Needs for the Year (appraiser fills)
    training_need_a = models.CharField(max_length=255, blank=True, default='')
    training_need_b = models.CharField(max_length=255, blank=True, default='')
    training_need_c = models.CharField(max_length=255, blank=True, default='')

    # Growth Prospects (appraiser fills)
    eligible_for_confirmation = models.BooleanField(null=True, blank=True)
    considered_for_additional_responsibilities = models.BooleanField(null=True, blank=True)

    # MGMT / HR Remarks
    mgmt_hr_remarks = models.TextField(blank=True, default='')
    extra_appraiser_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.employee.emp_id} - {self.period_from} to {self.period_to}"

class KRATemplate(models.Model):
    """HR-designed master KRA structure. Single instance used as the template for all staff appraisals."""
    frame_config = models.JSONField(default=default_frame_config, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'KRA Template'

    def __str__(self):
        return f"KRA Template (updated {self.updated_at})"


class KRATemplateRow(models.Model):
    template = models.ForeignKey(KRATemplate, on_delete=models.CASCADE, related_name='rows')
    section = models.CharField(max_length=30)
    sl_no = models.PositiveIntegerField(default=1)
    max_mark = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        ordering = ['section', 'sl_no']

    def __str__(self):
        return f"{self.section} row {self.sl_no} ({self.max_mark})"


class KRA(models.Model):
    SECTION_KRA = 'kra_objectives'
    SECTION_COMPETENCIES = 'competencies'
    SECTION_BEHAVIOUR = 'behaviour'
    SECTION_CHOICES = [
        (SECTION_KRA, 'KRA Objectives'),
        (SECTION_COMPETENCIES, 'Competencies'),
        (SECTION_BEHAVIOUR, 'Behaviour'),
    ]

    appraisal = models.ForeignKey(Appraisal, on_delete=models.CASCADE, related_name='kras')
    section = models.CharField(max_length=30, choices=SECTION_CHOICES, default=SECTION_KRA)
    sl_no = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=255, default='')                  # e.g. "Customer Satisfaction"
    description = models.TextField(blank=True, default='')                # e.g. "Resolve 99% of reported issues..."
    max_mark = models.DecimalField(max_digits=6, decimal_places=2, default=0)  # e.g. 25
    appraisee_mark = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)  # staff fills
    appraiser_mark = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)  # appraiser fills
    reviewer_mark = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)   # reviewer fills

    class Meta:
        ordering = ['section', 'sl_no']

    def __str__(self):
        return f"{self.appraisal.employee.emp_id} - {self.section} - {self.title}"
