from datetime import date

from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from django.db.models import Count
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from .serializers import (
    AppraisalSerializer,
    AppraiserAppraisalSerializer,
    ReviewerAppraisalSerializer,
    HRAppraisalSerializer,
    StaffAppraisalSerializer,
    KRASerializer,
    StaffKRASerializer,
    KRATemplateSerializer,
)
from .models import Appraisal, KRA, KRATemplate, KRATemplateRow
from employees.models import Employee


def _parse_period_date(value, field_name):
    if value in (None, ''):
        return None
    parsed = parse_date(str(value).strip())
    if not parsed:
        raise ValidationError({field_name: 'Invalid date format. Use YYYY-MM-DD.'})
    return parsed


def _parse_period_filters(params, allow_swap=False):
    filter_start = _parse_period_date(params.get('period_from'), 'period_from')
    filter_end = _parse_period_date(params.get('period_to'), 'period_to')

    if filter_start and filter_end and filter_start > filter_end:
        if allow_swap:
            filter_start, filter_end = filter_end, filter_start
        else:
            raise ValidationError({'period_from': 'period_from cannot be greater than period_to.'})

    return filter_start, filter_end


def _apply_period_overlap_filter(qs, filter_start, filter_end, start_field='period_from', end_field='period_to'):
    if not filter_start and not filter_end:
        return qs

    qs = qs.annotate(
        appraisal_start=Coalesce(start_field, end_field),
        appraisal_end=Coalesce(end_field, start_field),
    ).exclude(appraisal_start__isnull=True).exclude(appraisal_end__isnull=True)

    if filter_start:
        qs = qs.filter(appraisal_end__gte=filter_start)
    if filter_end:
        qs = qs.filter(appraisal_start__lte=filter_end)
    return qs


def _parse_int_list(raw_value, field_name):
    if raw_value in (None, ''):
        return None

    values = raw_value
    if not isinstance(values, (list, tuple)):
        values = str(raw_value).split(',')

    parsed = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if not text.isdigit():
            raise ValidationError({field_name: f'Invalid integer value: {text}'})
        parsed.append(int(text))
    return parsed


def get_common_structure_source(exclude_appraisal_id=None):
    qs = Appraisal.objects.prefetch_related('kras').filter(employee__role=Employee.ROLE_STAFF)
    if exclude_appraisal_id:
        qs = qs.exclude(pk=exclude_appraisal_id)

    source = qs.filter(kras__isnull=False).distinct().order_by('-updated_at', '-id').first()
    if source:
        return source
    return qs.order_by('-updated_at', '-id').first()


def clone_common_structure(appraisal):
    """Clone HR's master KRATemplate into a new/empty appraisal."""
    template = KRATemplate.objects.prefetch_related('rows').order_by('-id').first()
    if not template:
        return

    appraisal.frame_config = template.frame_config
    appraisal.save(update_fields=['frame_config'])

    if appraisal.kras.exists():
        return

    rows = list(template.rows.all())
    if not rows:
        return

    KRA.objects.bulk_create([
        KRA(
            appraisal=appraisal,
            section=row.section,
            sl_no=row.sl_no,
            title='',
            description='',
            max_mark=row.max_mark,
        )
        for row in rows
    ])


def ensure_current_year_appraisals(employee_qs):
    employee_ids = list(employee_qs.values_list('id', flat=True))
    if not employee_ids:
        return

    today = date.today()
    period_from = date(today.year, 1, 1)
    period_to = date(today.year, 12, 31)

    existing_emp_ids = set(
        Appraisal.objects.filter(employee_id__in=employee_ids).values_list('employee_id', flat=True)
    )
    missing_emp_ids = [emp_id for emp_id in employee_ids if emp_id not in existing_emp_ids]

    if missing_emp_ids:
        Appraisal.objects.bulk_create([
            Appraisal(
                employee_id=emp_id,
                appraisal_type='Annual',
                period_from=period_from,
                period_to=period_to,
                status=Appraisal.STATUS_DRAFT,
            )
            for emp_id in missing_emp_ids
        ])

    appraisals = list(Appraisal.objects.filter(employee_id__in=employee_ids))
    appraisal_ids = [app.id for app in appraisals]
    if not appraisal_ids:
        return

    appraisal_ids_with_kras = set(
        KRA.objects.filter(appraisal_id__in=appraisal_ids).values_list('appraisal_id', flat=True).distinct()
    )
    empty_appraisals = [app for app in appraisals if app.id not in appraisal_ids_with_kras]

    if not empty_appraisals:
        return

    template = KRATemplate.objects.prefetch_related('rows').order_by('-id').first()
    if not template:
        return

    rows = list(template.rows.all())
    if not rows:
        return

    appraisals_to_update = [app for app in empty_appraisals if app.frame_config != template.frame_config]
    if appraisals_to_update:
        for app in appraisals_to_update:
            app.frame_config = template.frame_config
        Appraisal.objects.bulk_update(appraisals_to_update, ['frame_config'])

    KRA.objects.bulk_create([
        KRA(
            appraisal_id=app.id,
            section=row.section,
            sl_no=row.sl_no,
            title='',
            description='',
            max_mark=row.max_mark,
        )
        for app in empty_appraisals
        for row in rows
    ])


class IsAuthenticatedEmployee(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and hasattr(request.user, 'employee'))


class IsAppraiserOrReviewerOrHR(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated or not hasattr(request.user, 'employee'):
            return False
        return request.user.employee.role in {Employee.ROLE_APPRAISER, Employee.ROLE_REVIEWER, Employee.ROLE_HR}


# ── Appraisal endpoints ──

class AppraisalListCreateAPI(generics.ListCreateAPIView):
    serializer_class = AppraisalSerializer
    permission_classes = [IsAuthenticatedEmployee]

    def _filter_qs(self, qs):
        employee = self.request.user.employee
        if employee.role == Employee.ROLE_HR:
            return qs.all()
        if employee.role == Employee.ROLE_REVIEWER:
            dept_ids = list(employee.reviewer_departments.values_list('id', flat=True))
            reviewer_qs = qs.filter(employee__reviewer=employee)
            return reviewer_qs.filter(employee__department_id__in=dept_ids) if dept_ids else reviewer_qs
        if employee.role == Employee.ROLE_APPRAISER:
            dept_ids = list(employee.appraiser_departments.values_list('id', flat=True))
            appraiser_qs = qs.filter(employee__appraiser=employee)
            return appraiser_qs.filter(employee__department_id__in=dept_ids) if dept_ids else appraiser_qs
        return qs.filter(employee=employee)

    def get_queryset(self):
        employee = self.request.user.employee
        filter_start, filter_end = _parse_period_filters(self.request.query_params)

        if employee.role == Employee.ROLE_HR:
            visible_employees = Employee.objects.filter(role=Employee.ROLE_STAFF)
        elif employee.role == Employee.ROLE_REVIEWER:
            dept_ids = list(employee.reviewer_departments.values_list('id', flat=True))
            visible_employees = Employee.objects.filter(
                role=Employee.ROLE_STAFF,
                reviewer=employee,
            )
            if dept_ids:
                visible_employees = visible_employees.filter(department_id__in=dept_ids)
        elif employee.role == Employee.ROLE_APPRAISER:
            dept_ids = list(employee.appraiser_departments.values_list('id', flat=True))
            visible_employees = Employee.objects.filter(role=Employee.ROLE_STAFF, appraiser=employee)
            if dept_ids:
                visible_employees = visible_employees.filter(department_id__in=dept_ids)
        else:
            visible_employees = Employee.objects.filter(pk=employee.pk)

        ensure_current_year_appraisals(visible_employees)

        qs = Appraisal.objects.select_related(
            'employee',
            'employee__user',
            'employee__department',
            'employee__appraiser__user',
            'employee__reviewer__user',
        ).prefetch_related('kras').order_by(
            'employee__department__name',
            'employee__user__first_name',
            'employee__user__last_name',
        )
        qs = self._filter_qs(qs)
        return _apply_period_overlap_filter(qs, filter_start, filter_end)

    def get_serializer_class(self):
        employee = self.request.user.employee
        if employee.role == Employee.ROLE_HR:
            return HRAppraisalSerializer
        if employee.role == Employee.ROLE_APPRAISER:
            return AppraiserAppraisalSerializer
        if employee.role == Employee.ROLE_REVIEWER:
            return ReviewerAppraisalSerializer
        return StaffAppraisalSerializer

    def perform_create(self, serializer):
        if self.request.user.employee.role not in {Employee.ROLE_APPRAISER, Employee.ROLE_REVIEWER, Employee.ROLE_HR}:
            raise PermissionDenied('Only appraisers, reviewers and HR can create appraisals.')
        serializer.save()


class AppraisalDetailAPI(generics.RetrieveUpdateAPIView):
    serializer_class = AppraisalSerializer
    permission_classes = [IsAuthenticatedEmployee]

    def _filter_qs(self, qs):
        employee = self.request.user.employee
        if employee.role == Employee.ROLE_HR:
            return qs.all()
        if employee.role == Employee.ROLE_REVIEWER:
            dept_ids = list(employee.reviewer_departments.values_list('id', flat=True))
            reviewer_qs = qs.filter(employee__reviewer=employee)
            reviewer_qs = reviewer_qs.filter(employee__department_id__in=dept_ids) if dept_ids else reviewer_qs
            # Also allow reviewer to access their own appraisal
            own_appraisal = qs.filter(employee=employee)
            return reviewer_qs | own_appraisal
        if employee.role == Employee.ROLE_APPRAISER:
            dept_ids = list(employee.appraiser_departments.values_list('id', flat=True))
            appraiser_qs = qs.filter(employee__appraiser=employee)
            appraiser_qs = appraiser_qs.filter(employee__department_id__in=dept_ids) if dept_ids else appraiser_qs
            # Also allow appraiser to access their own appraisal
            own_appraisal = qs.filter(employee=employee)
            return appraiser_qs | own_appraisal
        return qs.filter(employee=employee)

    def get_queryset(self):
        qs = Appraisal.objects.select_related(
            'employee',
            'employee__user',
            'employee__department',
            'employee__appraiser__user',
            'employee__reviewer__user',
        ).prefetch_related('kras')
        return self._filter_qs(qs)

    def get_serializer_class(self):
        employee = self.request.user.employee
        if employee.role == Employee.ROLE_HR:
            return HRAppraisalSerializer
        if employee.role == Employee.ROLE_APPRAISER:
            return AppraiserAppraisalSerializer
        if employee.role == Employee.ROLE_REVIEWER:
            return ReviewerAppraisalSerializer
        return StaffAppraisalSerializer

    def partial_update(self, request, *args, **kwargs):
        """Enforce status-based workflow rules on PATCH."""
        employee = request.user.employee
        appraisal = self.get_object()
        data = request.data

        # Determine if this is a submit action vs a save-draft action
        new_status = data.get('status')

        if employee.role == Employee.ROLE_STAFF:
            # Staff can only edit when status is Draft
            if appraisal.status != Appraisal.STATUS_DRAFT:
                raise PermissionDenied('You cannot edit after submission.')
            # Only allow submitting to Submitted — not jumping to other statuses
            if new_status and new_status != Appraisal.STATUS_SUBMITTED:
                raise PermissionDenied('Staff can only submit (not set other statuses).')

        elif employee.role == Employee.ROLE_APPRAISER:
            # Appraiser can only work on Submitted appraisals
            if appraisal.status == Appraisal.STATUS_DRAFT:
                raise PermissionDenied('Employee has not submitted yet.')
            if appraisal.status == Appraisal.STATUS_APPRAISER_REVIEWED and new_status is None:
                raise PermissionDenied('You have already submitted this appraisal.')
            # Only allow submitting to Appraiser Reviewed
            if new_status and new_status != Appraisal.STATUS_APPRAISER_REVIEWED:
                raise PermissionDenied('Appraisers can only advance status to Appraiser Reviewed.')

        elif employee.role == Employee.ROLE_REVIEWER:
            # Reviewer can only work when appraiser has reviewed
            if appraisal.status in (Appraisal.STATUS_DRAFT, Appraisal.STATUS_SUBMITTED):
                raise PermissionDenied('Appraiser has not submitted yet.')
            if appraisal.status == Appraisal.STATUS_REVIEWED and new_status is None:
                raise PermissionDenied('You have already submitted this appraisal.')
            # Only allow submitting to Reviewed
            if new_status and new_status != Appraisal.STATUS_REVIEWED:
                raise PermissionDenied('Reviewers can only advance status to Reviewed.')

        return super().partial_update(request, *args, **kwargs)


# ── KRA endpoints ──

class KRAListCreateAPI(generics.ListCreateAPIView):
    """
    GET  ?appraisal=<id>&section=kra_objectives  → list KRA items (filtered by role)
    POST                                         → appraiser/reviewer only
    """
    permission_classes = [IsAuthenticatedEmployee]

    def get_serializer_class(self):
        employee = self.request.user.employee
        if employee.role in {Employee.ROLE_APPRAISER, Employee.ROLE_REVIEWER, Employee.ROLE_HR}:
            return KRASerializer
        return StaffKRASerializer

    def get_queryset(self):
        employee = self.request.user.employee
        filter_start, filter_end = _parse_period_filters(self.request.query_params)
        qs = KRA.objects.select_related('appraisal', 'appraisal__employee')
        appraisal_id = self.request.query_params.get('appraisal')
        section = self.request.query_params.get('section')
        if appraisal_id:
            qs = qs.filter(appraisal_id=appraisal_id)
        if section:
            qs = qs.filter(section=section)
        if employee.role == Employee.ROLE_HR:
            scoped_qs = qs
        elif employee.role == Employee.ROLE_REVIEWER:
            dept_ids = list(employee.reviewer_departments.values_list('id', flat=True))
            reviewer_qs = qs.filter(appraisal__employee__reviewer=employee)
            scoped_qs = reviewer_qs.filter(appraisal__employee__department_id__in=dept_ids) if dept_ids else reviewer_qs
        elif employee.role == Employee.ROLE_APPRAISER:
            dept_ids = list(employee.appraiser_departments.values_list('id', flat=True))
            appraiser_qs = qs.filter(appraisal__employee__appraiser=employee)
            scoped_qs = appraiser_qs.filter(appraisal__employee__department_id__in=dept_ids) if dept_ids else appraiser_qs
        else:
            scoped_qs = qs.filter(appraisal__employee=employee)

        return _apply_period_overlap_filter(
            scoped_qs,
            filter_start,
            filter_end,
            start_field='appraisal__period_from',
            end_field='appraisal__period_to',
        )

    def perform_create(self, serializer):
        employee = self.request.user.employee
        if employee.role != Employee.ROLE_HR:
            raise PermissionDenied('Only HR can add or frame KRA structure.')

        serializer.save()


class KRADetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """
    GET  /kras/<id>/   → single KRA item
    PATCH              → staff can only update appraisee_mark; appraiser/reviewer/hr can update all
    """
    permission_classes = [IsAuthenticatedEmployee]

    def get_serializer_class(self):
        employee = self.request.user.employee
        if employee.role in {Employee.ROLE_APPRAISER, Employee.ROLE_REVIEWER, Employee.ROLE_HR}:
            return KRASerializer
        return StaffKRASerializer

    def get_queryset(self):
        employee = self.request.user.employee
        qs = KRA.objects.select_related('appraisal', 'appraisal__employee')
        if employee.role == Employee.ROLE_HR:
            return qs
        if employee.role == Employee.ROLE_REVIEWER:
            dept_ids = list(employee.reviewer_departments.values_list('id', flat=True))
            reviewer_qs = qs.filter(appraisal__employee__reviewer=employee)
            return reviewer_qs.filter(appraisal__employee__department_id__in=dept_ids) if dept_ids else reviewer_qs
        if employee.role == Employee.ROLE_APPRAISER:
            dept_ids = list(employee.appraiser_departments.values_list('id', flat=True))
            appraiser_qs = qs.filter(appraisal__employee__appraiser=employee)
            return appraiser_qs.filter(appraisal__employee__department_id__in=dept_ids) if dept_ids else appraiser_qs
        return qs.filter(appraisal__employee=employee)

    def partial_update(self, request, *args, **kwargs):
        employee = request.user.employee
        kra = self.get_object()
        appraisal = kra.appraisal
        mark_fields = {'appraisee_mark', 'appraiser_mark', 'reviewer_mark'}
        is_mark_update = any(field in request.data for field in mark_fields)

        if is_mark_update and employee.role != Employee.ROLE_HR and not appraisal.mark_entry_access_open:
            raise PermissionDenied('Mark entry is locked by HR.')

        # Status-based write restrictions
        if employee.role == Employee.ROLE_STAFF:
            if appraisal.status != Appraisal.STATUS_DRAFT:
                raise PermissionDenied('You cannot edit marks after submission.')

        elif employee.role == Employee.ROLE_APPRAISER:
            if appraisal.status == Appraisal.STATUS_DRAFT:
                raise PermissionDenied('Employee has not submitted yet.')
            if appraisal.status == Appraisal.STATUS_APPRAISER_REVIEWED:
                raise PermissionDenied('You have already submitted this appraisal.')
            allowed_fields = {'title', 'description', 'appraiser_mark'}
            invalid_fields = set(request.data.keys()) - allowed_fields
            if invalid_fields:
                raise PermissionDenied('Appraisers can only add content to the HR-framed KRA and enter their marks.')

        elif employee.role == Employee.ROLE_REVIEWER:
            if appraisal.status in (Appraisal.STATUS_DRAFT, Appraisal.STATUS_SUBMITTED):
                raise PermissionDenied('Appraiser has not submitted yet.')
            if appraisal.status == Appraisal.STATUS_REVIEWED:
                raise PermissionDenied('You have already submitted this appraisal.')
            allowed_fields = {'reviewer_mark'}
            invalid_fields = set(request.data.keys()) - allowed_fields
            if invalid_fields:
                raise PermissionDenied('Reviewers can only enter reviewer marks.')

        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        employee = request.user.employee
        if employee.role != Employee.ROLE_HR:
            raise PermissionDenied('Only HR can remove KRA items or change the step structure.')
        return super().destroy(request, *args, **kwargs)


class KRABulkCreateAPI(generics.CreateAPIView):
    """
    POST /kras/bulk/ → HR creates a list of KRA items at once for an appraisal section.
    Body: [ { appraisal, section, sl_no, title, description, max_mark }, ... ]
    """
    serializer_class = KRASerializer
    permission_classes = [IsAuthenticatedEmployee]

    def create(self, request, *args, **kwargs):
        if request.user.employee.role != Employee.ROLE_HR:
            raise PermissionDenied('Only HR can add or frame KRA structure.')
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


# ── Staff-only: my appraisals ──

class MyAppraisalAPI(generics.ListAPIView):
    serializer_class = StaffAppraisalSerializer
    permission_classes = [IsAuthenticatedEmployee]

    def get_queryset(self):
        employee = self.request.user.employee
        filter_start, filter_end = _parse_period_filters(self.request.query_params)
        ensure_current_year_appraisals(Employee.objects.filter(pk=employee.pk))
        qs = Appraisal.objects.select_related(
            'employee',
            'employee__user',
            'employee__department',
            'employee__appraiser__user',
            'employee__reviewer__user',
        ).prefetch_related('kras').filter(employee=employee)
        return _apply_period_overlap_filter(qs, filter_start, filter_end)


class AvailableAppraisalPeriodsAPI(generics.GenericAPIView):
    permission_classes = [IsAuthenticatedEmployee]

    def get(self, request, *args, **kwargs):
        employee = request.user.employee
        qs = Appraisal.objects.select_related('employee')

        if employee.role == Employee.ROLE_HR:
            qs = qs.all()
        elif employee.role == Employee.ROLE_REVIEWER:
            dept_ids = list(employee.reviewer_departments.values_list('id', flat=True))
            reviewer_qs = qs.filter(employee__reviewer=employee)
            qs = reviewer_qs.filter(employee__department_id__in=dept_ids) if dept_ids else reviewer_qs
        elif employee.role == Employee.ROLE_APPRAISER:
            dept_ids = list(employee.appraiser_departments.values_list('id', flat=True))
            appraiser_qs = qs.filter(employee__appraiser=employee)
            qs = appraiser_qs.filter(employee__department_id__in=dept_ids) if dept_ids else appraiser_qs
        else:
            qs = qs.filter(employee=employee)

        periods = (
            qs.exclude(period_from__isnull=True, period_to__isnull=True)
            .values('period_from', 'period_to')
            .annotate(appraisal_count=Count('id'))
            .order_by('-period_from', '-period_to')
        )
        return Response(list(periods), status=status.HTTP_200_OK)


class KRATemplateAPI(generics.GenericAPIView):
    """
    GET  /kra-template/  → returns the current HR-designed template (or empty)
    POST /kra-template/  → HR saves a new template and applies it to all existing staff appraisals
    """
    serializer_class = KRATemplateSerializer
    permission_classes = [IsAuthenticatedEmployee]

    def get(self, request, *args, **kwargs):
        filter_start, filter_end = _parse_period_filters(request.query_params)

        templates = KRATemplate.objects.prefetch_related('rows').order_by('-updated_at', '-id')
        if filter_start or filter_end:
            templates = _apply_period_overlap_filter(templates, filter_start, filter_end)
        template = templates.first()

        if not template:
            return Response(
                {
                    'id': None,
                    'frame_config': None,
                    'rows': [],
                    'period_from': None,
                    'period_to': None,
                    'updated_at': None,
                }
            )
        serializer = self.get_serializer(template)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        if request.user.employee.role != Employee.ROLE_HR:
            raise PermissionDenied('Only HR can update the KRA structure template.')

        frame_config = request.data.get('frame_config', {})
        rows_data = request.data.get('rows', [])

        if bool(request.data.get('period_from')) ^ bool(request.data.get('period_to')):
            raise ValidationError({'period': 'Both period_from and period_to are required together.'})
        filter_start, filter_end = _parse_period_filters(request.data)

        department_ids = _parse_int_list(request.data.get('department_ids'), 'department_ids')
        staff_ids = _parse_int_list(
            request.data.get('employee_ids', request.data.get('staff_ids')),
            'employee_ids',
        )

        # Upsert period-scoped template when a period is provided.
        template_qs = KRATemplate.objects.order_by('-id')
        if filter_start and filter_end:
            template_qs = template_qs.filter(period_from=filter_start, period_to=filter_end)
        else:
            template_qs = template_qs.filter(period_from__isnull=True, period_to__isnull=True)

        template = template_qs.first()
        if template:
            template.frame_config = frame_config
            template.period_from = filter_start
            template.period_to = filter_end
            template.save(update_fields=['frame_config', 'period_from', 'period_to', 'updated_at'])
            template.rows.all().delete()
        else:
            template = KRATemplate.objects.create(
                frame_config=frame_config,
                period_from=filter_start,
                period_to=filter_end,
            )

        KRATemplateRow.objects.bulk_create([
            KRATemplateRow(
                template=template,
                section=row['section'],
                sl_no=row['sl_no'],
                max_mark=row['max_mark'],
            )
            for row in rows_data
        ])

        # Apply structure to all existing staff appraisals
        from decimal import Decimal
        all_staff_appraisals = Appraisal.objects.filter(
            employee__role=Employee.ROLE_STAFF
        ).prefetch_related('kras')

        if department_ids is not None:
            all_staff_appraisals = all_staff_appraisals.filter(employee__department_id__in=department_ids)
        if staff_ids is not None:
            all_staff_appraisals = all_staff_appraisals.filter(employee_id__in=staff_ids)
        if filter_start or filter_end:
            all_staff_appraisals = _apply_period_overlap_filter(all_staff_appraisals, filter_start, filter_end)

        rows = list(template.rows.all())
        applied_count = all_staff_appraisals.count()
        for appraisal in all_staff_appraisals:
            appraisal.frame_config = frame_config
            appraisal.save(update_fields=['frame_config'])

            current_kras = {
                (kra.section, kra.sl_no): kra
                for kra in appraisal.kras.all()
            }
            new_keys = {(row.section, row.sl_no) for row in rows}

            # Delete KRAs not in new structure
            for key, kra in current_kras.items():
                if key not in new_keys:
                    kra.delete()

            # Create or update KRAs for each template row
            for row in rows:
                key = (row.section, row.sl_no)
                if key in current_kras:
                    kra = current_kras[key]
                    kra.max_mark = row.max_mark
                    kra.save(update_fields=['max_mark'])
                else:
                    KRA.objects.create(
                        appraisal=appraisal,
                        section=row.section,
                        sl_no=row.sl_no,
                        title='',
                        description='',
                        max_mark=row.max_mark,
                    )

        serializer = self.get_serializer(template)
        payload = serializer.data
        payload['applied_appraisal_count'] = applied_count
        return Response(payload, status=status.HTTP_200_OK)

