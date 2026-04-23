from django.db import models
from django.contrib.auth.models import User


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Employee(models.Model):
    ROLE_STAFF = 'staff'
    ROLE_APPRAISER = 'appraiser'
    ROLE_REVIEWER = 'reviewer'
    ROLE_HR = 'hr'
    ROLE_CHOICES = [
        (ROLE_STAFF, 'Staff'),
        (ROLE_APPRAISER, 'Appraiser'),
        (ROLE_REVIEWER, 'Reviewer'),
        (ROLE_HR, 'HR'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    emp_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='employees',
    )
    designation = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_STAFF)

    appraiser = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='appraisees'
    )

    reviewer = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='reviewees'
    )

    reviewer_departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name='reviewers',
    )

    appraiser_departments = models.ManyToManyField(
        Department,
        blank=True,
        related_name='appraisers',
    )

    GENDER_MALE = 'Male'
    GENDER_FEMALE = 'Female'
    GENDER_OTHER = 'Other'
    GENDER_CHOICES = [
        (GENDER_MALE, 'Male'),
        (GENDER_FEMALE, 'Female'),
        (GENDER_OTHER, 'Other'),
    ]

    date_of_joining = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, null=True, blank=True)

    def __str__(self):
        return f"{self.emp_id} - {self.user.get_full_name()}"
