from django.urls import path
from .views import (
    LoginView, MeView, DepartmentListCreateView, DepartmentDetailView, EmployeeListCreateView,
    EmployeeDetailView, ReviewerDepartmentsView, AppraiserDepartmentsView, DepartmentManagersView,
    EmployeeBulkImportView,
    ResetPasswordView, ChangePasswordView,
)

urlpatterns = [
    path('api/login/', LoginView.as_view(), name='api_login'),
    path('api/reset-password/', ResetPasswordView.as_view(), name='api_reset_password'),
    path('api/change-password/', ChangePasswordView.as_view(), name='api_change_password'),
    path('api/me/', MeView.as_view(), name='api_me'),
    path('api/departments/', DepartmentListCreateView.as_view(), name='api_departments'),
    path('api/departments/<int:pk>/', DepartmentDetailView.as_view(), name='api_department_detail'),
    path('api/employees/', EmployeeListCreateView.as_view(), name='api_employees'),
    path('api/employees/<int:pk>/', EmployeeDetailView.as_view(), name='api_employee_detail'),
    path('api/employees/import/', EmployeeBulkImportView.as_view(), name='api_employees_import'),
    path('api/employees/<int:pk>/reviewer-departments/', ReviewerDepartmentsView.as_view(), name='api_reviewer_departments'),
    path('api/employees/<int:pk>/appraiser-departments/', AppraiserDepartmentsView.as_view(), name='api_appraiser_departments'),
    path('api/department-managers/', DepartmentManagersView.as_view(), name='api_department_managers'),
]
