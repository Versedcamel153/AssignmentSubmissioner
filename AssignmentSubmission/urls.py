"""
URL configuration for AssSub project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from .views import (
    upload_students, upload_courses, 
    lists, register, login, submission, 
    dashboard, submissionCreation, admin_dashboard, 
    index, close_submission, download_submission_zip,
    check_id, send_otp, verify_otp, set_password,
    manage_students, manage_courses
    )

urlpatterns = [
    path('students/upload/', upload_students, name="upload-students"),
    path('courses/upload/', upload_courses, name="upload-courses"),
    path('lists/', lists, name='lists'),
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('submissions/<uuid:submission_id>/', submission, name='submission'),
    path('dashboard/', dashboard, name='dashboard'),
    path('submissions/create/', submissionCreation, name='submission-create'),
    path('', index, name='index'),
    path('dashboard-admin/', admin_dashboard, name='admin-dashboard'),
    path('close-submission/<uuid:submission_id>/', close_submission, name='close-submission'),
    path('download-zip/<uuid:submission_id>/', download_submission_zip, name='download-zip'),
    path('check_id/', check_id, name='check-id'),
    path('send-otp/', send_otp, name='send-otp'),
    path('verify-otp/', verify_otp, name='verify-otp'),
    path('set-password/', set_password, name='set-password'),
    path('closed-submissions/', admin_dashboard,{"status": "closed"}, name='closed-submissions'),
    path('active-submissions/', admin_dashboard, {"status": "active"}, name='active-submissions'),
# ] 
    path('students/', manage_students, name='manage-students'),
    path('courses/', manage_courses, name='manage-courses'),
]

