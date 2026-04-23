from django.urls import path
from django.views.generic import RedirectView
from .views import (
    AppraisalListCreateAPI,
    AppraisalDetailAPI,
    KRAListCreateAPI,
    KRADetailAPI,
    KRABulkCreateAPI,
    MyAppraisalAPI,
    KRATemplateAPI,
    DownloadAllStaffsPDFAPI,
)

urlpatterns = [
    path('', RedirectView.as_view(url='/appraisals/api/appraisals/', permanent=False)),
    path('api/appraisals/', AppraisalListCreateAPI.as_view(), name='api_appraisals'),
    path('api/appraisals/my/', MyAppraisalAPI.as_view(), name='api_my_appraisals'),
    path('api/appraisals/<int:pk>/', AppraisalDetailAPI.as_view(), name='api_appraisal_detail'),
    path('api/kras/', KRAListCreateAPI.as_view(), name='api_kras'),
    path('api/kras/bulk/', KRABulkCreateAPI.as_view(), name='api_kras_bulk'),
    path('api/kras/<int:pk>/', KRADetailAPI.as_view(), name='api_kra_detail'),
    path('api/kra-template/', KRATemplateAPI.as_view(), name='api_kra_template'),
    path('api/download/all-staffs-pdf/', DownloadAllStaffsPDFAPI.as_view(), name='api_download_all_staffs_pdf'),
    path('api/appraisals/download-all-staffs-pdf/', DownloadAllStaffsPDFAPI.as_view(), name='api_appraisals_download_all_staffs_pdf'),
]
