from django.contrib import admin
from .models import Submission, StudentSubmission, PreApprovedStudents
# Register your models here.

admin.site.register(Submission)
admin.site.register(StudentSubmission)
admin.site.register(PreApprovedStudents)