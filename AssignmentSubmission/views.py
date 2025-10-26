from django.shortcuts import render
from .models import (
    PreApprovedStudents,
    Submission,
    StudentSubmission,
    Courses,
    EmailOTP,
)
from .forms import (
    RegistrationForm,
    LoginForm,
    StudentSubmissionForm,
    SubmissionCreationForm,
)
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model, login as auth_login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
import io, os
import zipfile
from django.http import HttpResponse, Http404
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Count
from django.http import HttpResponse
from django.template.loader import render_to_string

# Create your views here.

User = get_user_model()


from django.contrib import messages
import pandas as pd

def upload_students(request):
    students = PreApprovedStudents.objects.all()
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")

        if not uploaded_file:
            messages.error(request, "Please select a file before uploading.", extra_tags="students")
            return render(request, "AssSub/students.html")

        try:
            df = pd.read_excel(uploaded_file)

            # Check required columns
            required_columns = ["INDEX NUMBER", "NAME", "EMAIL"]
            for col in required_columns:
                if col not in df.columns:
                    messages.error(
                        request,
                        f"The uploaded file is missing a required column: '{col}'. Please check your file.",
                        extra_tags="students",
                    )
                    return render(request, "AssSub/students.html", {"students": students})

            # Drop rows with missing IDs
            df = df.dropna(subset=["INDEX NUMBER"])

            if df.empty:
                messages.error(request, "No valid student IDs found in the file.", extra_tags="students")
                return render(request, "AssSub/students.html", {"students": students})

            for _, row in df.iterrows():
                PreApprovedStudents.objects.update_or_create(
                    student_id=str(row["INDEX NUMBER"]).strip(),
                    defaults={
                        "name": str(row.get("NAME", "")).strip(),
                        "email": str(row.get("EMAIL", "")).strip(),
                    },
                )

            messages.success(request, "Students uploaded successfully!", extra_tags="students")

        except ValueError:
            messages.error(
                request,
                "Invalid file format. Please upload a valid Excel (.xlsx or .xls) file.",
                extra_tags="students",
            )
        except Exception:
            messages.error(
                request,
                "Something went wrong while processing your file. Please check the file and try again.",
                extra_tags="students",
            )

        return render(request, "AssSub/students.html", {"students": students})

    return render(request, "AssSub/students.html", {"students": students})



def upload_courses(request):
    if request.method == "POST" and request.FILES["file"]:
        df = pd.read_excel(request.FILES["file"])

        for _, row in df.iterrows():
            Courses.objects.update_or_create(
                code=row["CODE"],
                # lecturer=row['LECTURER'],
                defaults={
                    "name": row["NAME"],
                },
            )
        return render(request, "AssSub/sucess.html")

    return render(request, "AssSub/upload_courses.html")


def lists(request):
    students = PreApprovedStudents.objects.all()
    courses = Courses.objects.all()
    return render(
        request, "AssSub/lists.html", {"students": students, "courses": courses}
    )


def check_id(request):
    student_id = request.POST.get("student_id")
    context = {}

    try:
        student = PreApprovedStudents.objects.get(student_id=student_id)
        context["student"] = student
        context["masked_email"] = mask_email(student.email)

        if student.is_verified:
            context["form_error"] = "Student already Verified. Please Login."
            return render(request, "AssSub/register.html", context)

        if request.htmx:
            return render(request, "AssSub/register-2.html", context)

    except PreApprovedStudents.DoesNotExist:
        context["form_error"] = "Invalid or Student ID not found"

        if request.htmx:
            return render(request, "AssSub/register.html", context)

    return render(request, "AssSub/register.html", context)


# Python logic for display
def mask_email(email):
    name, domain = email.split("@")
    if len(name) > 2:
        return f"{name[0]}{'*'*(len(name)-2)}{name[-1]}@{domain}"
    return f"{name[0]}***@{domain}"  # fallback for short names


from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import random


def send_otp(request):
    email = request.POST.get("email")
    existing_email = request.POST.get("student_email")
    student_id = request.POST.get("student_id")
    context = {}

    try:
        student = PreApprovedStudents.objects.get(student_id=student_id)
        context["student"] = student
        context["student_email"] = existing_email

        if email != existing_email:
            context["form_error"] = "Email does not match pre-approved email"
            return render(request, "AssSub/register-2.html", context)

    except PreApprovedStudents.DoesNotExist:
        return HttpResponse("No matching student found", status=400)

    otp = random.randint(100000, 999999)
    EmailOTP.objects.create(email=email, otp=otp)

    context["otp"] = otp
    context["masked_email"] = mask_email(email)

    # Send mail
    subject = "Your OTP Code"
    html_message = render_to_string("AssSub/otp_email.html", context)
    plain_message = render_to_string("AssSub/otp_email.txt", context)
    email_message = EmailMultiAlternatives(subject, plain_message, to=[email])
    email_message.attach_alternative(html_message, "text/html")
    email_message.send()
    return render(request, "AssSub/enter-otp.html", context)


def verify_otp(request):
    email = request.POST.get("student_email")
    student_id = request.POST.get("student_id")
    otp = "".join(request.POST.get(f"otp-{i}", "") for i in range(1, 7))
    print(email)
    print(student_id)
    print(otp)

    context = {
        "student": PreApprovedStudents.objects.filter(
            email=email, student_id=student_id
        ).first(),
        "e_email": email,
    }

    if not otp.isdigit() or len(otp) != 6:
        context["form_error"] = "Invalid OTP format"
        return render(request, "AssSub/enter-otp.html", context)

    try:
        record = EmailOTP.objects.filter(email=email, otp=otp).latest("created_at")
    except EmailOTP.DoesNotExist:
        context["form_error"] = "Invalid OTP"
        return render(request, "AssSub/enter-otp.html", context)

    if record.is_expired:
        context["form_error"] = "OTP expired"
        return render(request, "AssSub/enter-otp.html", context)

    if record.is_verified:
        context["form_error"] = "The OTP has already been used"
        return render(request, "AssSub/enter-otp.html", context)

    # OTP is valid
    record.is_verified = True
    record.save()

    student = context["student"]
    if student:
        student.is_verified = True
        student.save()

    return render(request, "AssSub/set-password.html", context)


def set_password(request):
    password1 = request.POST.get("password1")
    password2 = request.POST.get("password2")
    email = request.POST.get("student_email")
    student_id = request.POST.get("student_id")
    context = {}

    if password1 != password2:
        context["form_error"] = "Password mismatch"

    user = User(student_id=student_id, email=email)
    user.set_password(password1)
    user.save()

    return render(request, "AssSub/verified.html", context)


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data["student_id"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]

            messages.success(request, "Student found", extra_tags="register")

            user = User(student_id=student_id, email=email)
            user.set_password(password)  # ✅ Hashes the password securely
            user.save()

            record = PreApprovedStudents.objects.get(student_id=student_id)
            record.is_registered = True
            record.save()

            print("Success")
            return redirect("login")  # ✅ (typo fixed)

        else:
            print(f"Errors: {form.errors}")
            messages,
    else:
        form = RegistrationForm()

    return render(request, "AssSub/base.html", {"form": form})


def login(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            student_id = form.cleaned_data["student_id"]
            password = form.cleaned_data["password"]
            try:
                user = authenticate(request, username=student_id, password=password)
                if user is not None:
                    auth_login(request, user)
                    return redirect("dashboard")
                else:
                    print("Invalid credentials")
                    messages.error(request, "Invalid credentials", extra_tags="login")
            except User.DoesNotExist:
                print("User not registered")
    else:
        form = LoginForm(request.POST)
    return render(request, "AssSub/login.html", {"form": form})


@login_required
def submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)

    if not submission.is_open:
        messages.error(request, "The Submission is closed", extra_tags="submission")
        return redirect("dashboard")

    student_submission, created = StudentSubmission.objects.get_or_create(
        submission=submission, student=request.user
    )

    if request.method == "POST":
        old_file = (
            student_submission.file
            if student_submission and student_submission.file
            else None
        )
        uploaded_file = request.FILES.get("file")

        form = StudentSubmissionForm(
            request.POST,
            request.FILES,
            instance=student_submission,
            submission_instance=submission,
        )

        if form.is_valid():
            # Delete old file BEFORE saving new one to avoid name collision
            if uploaded_file and student_submission.file:
                old_path = student_submission.file.path
                if os.path.exists(old_path):
                    student_submission.file.delete(save=False)  # clear from storage
                    student_submission.file = None  # clear from model
                    print("Old file deleted")

            new_submission = form.save(commit=False)
            new_submission.submission = submission
            new_submission.student = request.user
            new_submission.submitted_at = timezone.now()
            new_submission.save()

            messages.success(request, "Submission successful", extra_tags="submission")

            html = render_to_string("AssSub/check.html", {}, request=request)
            print("OK")
            return HttpResponse(html)

    else:
        form = StudentSubmissionForm(
            instance=student_submission, submission_instance=submission
        )

    context = {
        "form": form,
        "submission": submission,
        "existing_file": (
            student_submission.file.url
            if student_submission and student_submission.file
            else None
        ),
        "is_update": student_submission is not None,
    }

    if hasattr(request, "htmx") and request.htmx:
        return render(request, "AssSub/submission.html", context)

    return render(request, "AssSub/submission.html", context)


def submissionCreation(request):
    if request.method == "POST":
        print("POST recieved")
        form = SubmissionCreationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Submission created sucessfully",
                extra_tags="submission-creation",
            )
            print("OK")
            html = render_to_string("AssSub/check.html", {}, request=request)
            return HttpResponse(html)
    else:
        form = SubmissionCreationForm()
        print(f"errrs: {form.errors}")

    return render(request, "AssSub/submission_creation.html", {"form": form})


def close_submission(request, submission_id):
    submission = get_object_or_404(Submission, id=submission_id)
    if request.method == "POST":
        submission.is_open = False
        submission.save()
        messages.success(
            request, "Submission closed successfully", extra_tags="close-submission"
        )
        return redirect("admin-dashboard")
    return HttpResponse("Method not allowed", status=405)


def index(request):
    return render(request, "AssSub/redisgn1.html")


def download_submission_zip(request, submission_id):
    # Ensure the submission exists
    try:
        submission = Submission.objects.get(id=submission_id)
    except Submission.DoesNotExist:
        raise Http404("Submission not found")

    # Define the folder path where files are stored
    folder_path = os.path.join(settings.MEDIA_ROOT, "submissions", str(submission.id))

    if not os.path.exists(folder_path):
        raise Http404("No submissions found for this assignment")

    # Create ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                zip_file.write(file_path, arcname=file_name)  # Flat structure

    zip_buffer.seek(0)

    # Prepare response
    response = HttpResponse(zip_buffer, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="submission_{submission.course}_files.zip"'
    )
    return response


@login_required
def admin_dashboard(request, status=None):
    sort_field = request.GET.get("sort", "created_at")
    form = SubmissionCreationForm(request.POST)
    sort_dir = request.GET.get("dir", "desc")
    ordering = f"-{sort_field}" if sort_dir == "desc" else sort_field

    submissions = Submission.objects.annotate(
        num_submitted=Count("studentsubmission")
    ).order_by(ordering)

    # Filter by status
    # if status == "active":
    #     submissions = 
    # elif status == "closed":
    #     submissions = submissions.filter(is_open=False)

    # Calculate ratios
    total_students = PreApprovedStudents.objects.count()
    for submission in submissions:
        submission.submission_ratio = (
            (submission.num_submitted / total_students) * 100
            if total_students > 0
            else 0
        )

    submitted = StudentSubmission.objects.select_related(
        "submission", "student"
    ).filter(student=request.user)

    filter_param = status or request.GET.get("status", "all")
    if filter_param == "active":
        submissions = submissions.filter(is_open=True)
    elif filter_param == "closed":
        submissions = submissions.filter(is_open=False)

    context = {
        "submissions": submissions,
        # "submitteds": submitted,
        "total_students": total_students,
        # "sort": sort_field,
        # "dir": sort_dir,
        "form": form,
        "filter_param": filter_param,
    }

    if request.headers.get("HX-Request"):
        return render(request, "AssSub/partials/_admin_submissions_list.html", context)

    template = "AssSub/admin_dashboard.html"  # default
    if status == "active":
        template = "AssSub/active_submissions.html"
    elif status == "closed":
        template = "AssSub/closed_submissions.html"

    return render(request, template, context)


@login_required
def dashboard(request, status=None):
    # See all open submissions
    form = SubmissionCreationForm(request.POST)
    open_submissions = Submission.objects.filter(is_open=True).order_by("-created_at")
    close_submissions = Submission.objects.filter(is_open=False).order_by("-created_at")
    all_submissions = open_submissions | close_submissions
    submissions = all_submissions.order_by("-created_at")

    # See what the current user has already submitted
    assignments = Submission.objects.all()
    submitted = StudentSubmission.objects.select_related(
        "submission", "student"
    ).filter(student=request.user)
    submitted_map = {s.submission_id: s for s in submitted}

    for submission in submissions:
        submission.submission_data = submitted_map.get(submission.id)
        submission.has_submitted = submission.id in submitted_map
        submission.submitted_at = submitted_map.get(submission.id).submitted_at if submission.has_submitted else None
        
    for open in open_submissions:
        open.has_submitted = open.id in submitted_map
        open.submitted_at = submitted_map.get(open.id).submitted_at if open.has_submitted else None
        open.submission_data = submitted_map.get(open.id) if open.has_submitted else None


    filter_param = status or request.GET.get("filter", "all")

    if filter_param == "submitted":
        submissions = [s for s in submissions if s.has_submitted]
    elif filter_param == "not-submitted":
        submissions = [s for s in submissions if not s.has_submitted]
    # "all" = no filtering

    context = {
        "form": form,
        "submissions": submissions,
        "filter_param": filter_param,
    }

    if request.headers.get("HX-Request"):
        return render(request, "AssSub/partials/_submission_list.html", context)

    return render(
        request,
        "AssSub/dashboard.html",
        {
            "assignments": assignments,
            "submissions": submissions,
            "open_submissions": open_submissions,
            "close_submissions": close_submissions,
            "past_submissions": submitted,
            "form": form,
            "filter": filter_param,
        },
    )

def manage_students(request):
    students = PreApprovedStudents.objects.all()
    return render(request, "AssSub/students.html", {"students": students})

def manage_courses(request):
    courses = Courses.objects.all()
    return render(request, "AssSub/courses.html", {"courses": courses})