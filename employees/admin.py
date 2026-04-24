from django.contrib import admin
from .models import Department, Employee, EmployeeMemo


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('emp_id', 'user', 'role', 'department', 'designation', 'appraiser', 'reviewer', 'is_active')
    list_filter = ('role', 'department')
    search_fields = ('emp_id', 'user__username', 'user__first_name', 'user__last_name')
    fieldsets = (
        (None, {
            'fields': ('user', 'emp_id', 'department', 'designation', 'role', 'date_of_joining', 'is_active')
        }),
        ('Reporting', {
            'fields': ('appraiser', 'reviewer')
        }),
    )


@admin.register(EmployeeMemo)
class EmployeeMemoAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'created_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('employee__emp_id', 'employee__user__first_name', 'employee__user__last_name', 'memo')


# ── Proxy models for separate admin sections ──

class AppraiserDuty(Employee):
    class Meta:
        proxy = True
        verbose_name = 'Appraiser Duty'
        verbose_name_plural = 'Appraiser Duties'


class ReviewerDuty(Employee):
    class Meta:
        proxy = True
        verbose_name = 'Reviewer Duty'
        verbose_name_plural = 'Reviewer Duties'


@admin.register(AppraiserDuty)
class AppraiserDutyAdmin(admin.ModelAdmin):
    list_display = ('emp_id', 'user', 'department', 'get_assigned_departments')
    list_filter = ('department',)
    search_fields = ('emp_id', 'user__username', 'user__first_name', 'user__last_name')
    filter_horizontal = ('appraiser_departments',)
    fields = ('user', 'emp_id', 'department', 'appraiser_departments')
    readonly_fields = ('user', 'emp_id', 'department')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=Employee.ROLE_APPRAISER)

    def get_assigned_departments(self, obj):
        return ', '.join(d.name for d in obj.appraiser_departments.all())
    get_assigned_departments.short_description = 'Assigned Departments'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ReviewerDuty)
class ReviewerDutyAdmin(admin.ModelAdmin):
    list_display = ('emp_id', 'user', 'department', 'get_assigned_departments')
    list_filter = ('department',)
    search_fields = ('emp_id', 'user__username', 'user__first_name', 'user__last_name')
    filter_horizontal = ('reviewer_departments',)
    fields = ('user', 'emp_id', 'department', 'reviewer_departments')
    readonly_fields = ('user', 'emp_id', 'department')

    def get_queryset(self, request):
        return super().get_queryset(request).filter(role=Employee.ROLE_REVIEWER)

    def get_assigned_departments(self, obj):
        return ', '.join(d.name for d in obj.reviewer_departments.all())
    get_assigned_departments.short_description = 'Assigned Departments'

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
