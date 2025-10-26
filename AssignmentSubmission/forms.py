from .models import PreApprovedStudents, StudentSubmission, Submission
from django import forms

class RegistrationForm(forms.Form):
    student_id = forms.CharField(label="Student ID")
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        student_id = cleaned_data.get('student_id')

        if not student_id:
            return cleaned_data  # Skip if student_id is missing

        try:
            record = PreApprovedStudents.objects.get(student_id=student_id)
        except PreApprovedStudents.DoesNotExist:
            self.add_error('student_id', "Student ID not found in class list.")
        else:
            if record.is_registered:
                self.add_error('student_id', "Student is already registered.")

        return cleaned_data

class LoginForm(forms.Form):
    student_id = forms.CharField(label="Student ID")
    password = forms.CharField(widget=forms.PasswordInput)

class StudentSubmissionForm(forms.ModelForm):
    class Meta:
        model = StudentSubmission
        fields = ['file']

    def __init__(self, *args, **kwargs):
        self.submission_instance = kwargs.pop('submission_instance', None)
        super().__init__(*args, **kwargs)

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if self.submission_instance:
            allowed_extension = self.submission_instance.format  # e.g. ".pdf"
            if not file.name.lower().endswith(allowed_extension):
                raise forms.ValidationError(
                    f"The file must be in {allowed_extension} format."
                )
        return file
    
class SubmissionCreationForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['title', 'course', 'format', 'deadline', 'note' ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].empty_label = "-- Select Course --"
        self.fields['format'].empty_label = "--Select Format--"