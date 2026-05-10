from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def get_default_expiration():
    """Return expiration date 30 days from now"""
    return timezone.now() + timezone.timedelta(days=30)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_("email address"), unique=True)
    first_name = models.CharField(_("first name"), max_length=30, blank=True)
    last_name = models.CharField(_("last name"), max_length=30, blank=True)
    is_active = models.BooleanField(_("active"), default=True)
    is_staff = models.BooleanField(_("staff status"), default=False)
    date_joined = models.DateTimeField(_("date joined"), default=timezone.now)

    # Business-specific fields
    job_title = models.CharField(_("job title"), max_length=100, blank=True)
    can_create_quotes = models.BooleanField(default=False)
    can_approve_quotes = models.BooleanField(default=False)
    can_access_financials = models.BooleanField(default=False)

    # For social auth
    is_social_account = models.BooleanField(default=False)
    social_provider = models.CharField(max_length=30, blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name


class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)

    def __str__(self):
        return self.company


class Service(models.Model):
    UNIT_TYPE_CHOICES = [
        ("ft", "Linear Feet"),
        ("sqft", "Square Feet"),
        ("hour", "Hour"),
        ("item", "Per Item"),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    default_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_type = models.CharField(
        max_length=20,
        choices=UNIT_TYPE_CHOICES,
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (${self.default_price}/{self.unit_type})"

    def get_name_en(self):
        parts = self.name.split("|`", 1)
        return parts[0].strip()

    def get_name_fr(self):
        parts = self.name.split("|`", 1)
        if len(parts) <= 1 or not parts[1].strip():
            return self.get_name_en()
        return parts[1].strip()

    def get_description_en(self):
        parts = self.description.split("|`", 1)
        return parts[0].strip()

    def get_description_fr(self):
        parts = self.description.split("|`", 1)
        if len(parts) <= 1 or not parts[1].strip():
            return self.get_description_en()
        return parts[1].strip()


class Quote(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("sent", "Sent to Client"),
        ("viewed", "Viewed by Client"),
        ("quote_viewed", "Quote Viewed by Client"),
        ("invoice_viewed", "Invoice Viewed by Client"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("expired", "Expired"),
        ("modified", "Modified (Locked)"),
        ("invoice", "Invoice"),
    ]

    TIME_PERIOD_CHOICES = [
        ("standard", "8am-5pm"),
        ("evening", "5pm-2am"),
        ("night", "9pm-2am"),
        ("weekend", "Weekend/Holiday"),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="quotes")
    title = models.CharField(max_length=200, default="Line Striping Quote")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_default_expiration)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    invoice_number = models.CharField(max_length=20, unique=True)

    time_period = models.CharField(
        max_length=20, choices=TIME_PERIOD_CHOICES, default="standard"
    )
    evening_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    weekend_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    number_of_days = models.IntegerField(default=1)

    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Access security
    access_token = models.CharField(max_length=32, unique=True, editable=False)
    verification_code = models.CharField(max_length=6, editable=False)

    sent_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)
    job_location = models.TextField(blank=True)
    expected_completion_date = models.DateField(null=True, blank=True)

    original_quote = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="versions",
    )

    def __str__(self):
        return f"Quote {self.id} for {self.client.name}"

    def save(self, *args, **kwargs):
        create_follow_up = False
        if self.pk:
            try:
                old_quote = Quote.objects.get(pk=self.pk)
                if old_quote.status != "sent" and self.status == "sent":
                    create_follow_up = True
                    self.sent_at = timezone.now()
            except Quote.DoesNotExist:
                pass

        if not self.access_token:
            # Generate token on first save
            import random
            import secrets

            self.access_token = secrets.token_hex(16)
            self.verification_code = "".join(
                [str(random.randint(0, 9)) for _ in range(6)]
            )

        if not self.invoice_number:
            self.invoice_number = self.generate_invoice_number()

        super().save(*args, **kwargs)

        if create_follow_up:
            self.create_quote_follow_up()

    def generate_invoice_number(self):
        """Generate in format Q0525-201 or INV0525-201"""
        from datetime import datetime

        now = datetime.now()
        month_year = now.strftime("%m%y")

        if self.status == "invoice":
            prefix = "INV"
        else:
            prefix = "Q"

        # If this is a modification of an existing quote, increment by 1
        if self.original_quote:
            original_number = self.original_quote.invoice_number
            try:
                base_part, number_part = original_number.split("-")
                original_month_year = "".join(c for c in base_part if c.isdigit())
                new_number = int(number_part) + 1
                return f"{prefix}{original_month_year}-{new_number}"
            except (ValueError, IndexError):
                pass

        # For new quotes, keep a gap of 10 from the last one
        existing_numbers = Quote.objects.filter(
            invoice_number__startswith=f"{prefix}{month_year}-"
        ).values_list("invoice_number", flat=True)

        base_number = 201
        used_numbers = set()

        for number_str in existing_numbers:
            try:
                last_part = int(number_str.split("-")[-1])
                used_numbers.add(last_part)
            except (ValueError, IndexError):
                continue

        # Find the next available "base" number (multiples of 10 + 1)
        # 201, 211, 221, 231, etc.
        current_base = base_number
        while True:
            group_used = any(
                num in used_numbers for num in range(current_base, current_base + 10)
            )
            if not group_used:
                return f"{prefix}{month_year}-{current_base}"
            current_base += 10

    def create_modification(self):
        if self.status in ["modified", "invoice"]:
            raise ValueError(
                "Cannot modify a quote that is already modified or invoiced"
            )

        self.status = "modified"
        self.save()

        new_quote = Quote.objects.create(
            client=self.client,
            title=self.title,
            expires_at=self.expires_at,
            time_period=self.time_period,
            evening_fee=self.evening_fee,
            weekend_fee=self.weekend_fee,
            number_of_days=self.number_of_days,
            discount_percentage=self.discount_percentage,
            notes=self.notes,
            job_location=self.job_location,
            expected_completion_date=self.expected_completion_date,
            original_quote=self.original_quote or self,
            status="draft",
        )

        for item in self.items.all():
            QuoteItem.objects.create(
                quote=new_quote,
                service=item.service,
                quantity=item.quantity,
                unit_price=item.unit_price,
                notes=item.notes,
            )

        return new_quote

    def create_invoice(self):
        if not self.can_be_invoiced:
            raise ValueError("Can only create invoice from accepted quotes")

        invoice = Quote.objects.create(
            client=self.client,
            title=f"Invoice - {self.title}",
            expires_at=self.expires_at,
            time_period=self.time_period,
            evening_fee=self.evening_fee,
            weekend_fee=self.weekend_fee,
            number_of_days=self.number_of_days,
            discount_percentage=self.discount_percentage,
            notes=self.notes,
            job_location=self.job_location,
            expected_completion_date=self.expected_completion_date,
            original_quote=self,
            status="invoice",
        )

        for item in self.items.all():
            QuoteItem.objects.create(
                quote=invoice,
                service=item.service,
                quantity=item.quantity,
                unit_price=item.unit_price,
                notes=item.notes,
            )

        return invoice

    def create_quote_follow_up(self, days_after=5):
        follow_up_date = timezone.now().date() + timedelta(days=days_after)

        FollowUp.objects.create(
            quote=self,
            due_date=follow_up_date,
            notes="Check if client has reviewed the quote",
        )

    @property
    def subtotal(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def time_period_fee(self):
        if self.time_period == "evening":
            return self.evening_fee
        elif self.time_period == "weekend":
            return self.weekend_fee
        return 0

    @property
    def discount_amount(self):
        return (self.subtotal * self.discount_percentage) / 100

    @property
    def total_amount(self):
        return self.subtotal + self.time_period_fee - self.discount_amount

    @property
    def tps_amount(self):
        return round(self.total_amount * Decimal("0.05"), 2)

    @property
    def tvq_amount(self):
        return round(self.total_amount * Decimal("0.09975"), 2)

    @property
    def final_total(self):
        return round(self.total_amount + self.tps_amount + self.tvq_amount, 2)

    @property
    def can_be_modified(self):
        return self.status not in ["modified", "invoice", "accepted"]

    @property
    def can_be_invoiced(self):
        return self.status in ["accepted", "sent", "viewed", "quote_viewed"]

    @property
    def is_invoice(self):
        return self.status in ["invoice", "invoice_viewed"]


class QuoteVisit(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="visits")
    visited_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)

    class Meta:
        ordering = ["-visited_at"]

    def __str__(self):
        return f"Visit to {self.quote} at {self.visited_at:%Y-%m-%d %H:%M:%S}"


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    total_price = models.GeneratedField(
        expression=models.F("quantity") * models.F("unit_price"),
        output_field=models.DecimalField(max_digits=10, decimal_places=2),
        db_persist=True,
    )

    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # Set unit price from service if not specified
        if self.unit_price is None:
            self.unit_price = self.service.default_price
        super().save(*args, **kwargs)


# class Job(models.Model):
#     STATUS_CHOICES = [
#         ("scheduled", "Scheduled"),
#         ("in_progress", "In Progress"),
#         ("completed", "Completed"),
#         ("cancelled", "Cancelled"),
#     ]

#     quote = models.OneToOneField(Quote, on_delete=models.CASCADE, related_name="job")
#     scheduled_start = models.DateTimeField()
#     scheduled_end = models.DateTimeField()
#     actual_start = models.DateTimeField(null=True, blank=True)
#     actual_end = models.DateTimeField(null=True, blank=True)
#     status = models.CharField(
#         max_length=20, choices=STATUS_CHOICES, default="scheduled"
#     )
#     notes = models.TextField(blank=True)


# class MaterialUsage(models.Model):
#     job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="materials")
#     material_type = models.CharField(
#         max_length=100
#     )  # e.g., "Yellow Paint", "White Paint"
#     quantity = models.DecimalField(max_digits=10, decimal_places=2)
#     unit = models.CharField(max_length=20)  # e.g., "gallon", "can"
#     cost = models.DecimalField(max_digits=10, decimal_places=2)
#     date_recorded = models.DateTimeField(auto_now_add=True)


# class TimeEntry(models.Model):
#     job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="time_entries")
#     staff = models.ForeignKey(
#         "CustomUser", on_delete=models.CASCADE, related_name="time_entries"
#     )
#     start_time = models.DateTimeField()
#     end_time = models.DateTimeField(null=True, blank=True)
#     description = models.TextField(blank=True)

#     @property
#     def duration(self):
#         if self.end_time:
#             return self.end_time - self.start_time
#         return None


# class JobPhoto(models.Model):
#     job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="photos")
#     image = models.ImageField(upload_to="job_photos/")
#     caption = models.CharField(max_length=200, blank=True)
#     photo_type = models.CharField(
#         max_length=20,
#         choices=[("before", "Before"), ("during", "During Work"), ("after", "After")],
#         default="during",
#     )
#     uploaded_at = models.DateTimeField(auto_now_add=True)
#     uploaded_by = models.ForeignKey(
#         "CustomUser",
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name="uploaded_photos",
#     )

# class JobWeather(models.Model):
#     job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name="weather")
#     weather_conditions = models.TextField(blank=True)
#     temperature = models.DecimalField(max_digits=5, decimal_places=2)
#     wind_speed = models.DecimalField(max_digits=5, decimal_places=2)
#     precipitation = models.DecimalField(max_digits=5, decimal_places=2)


class BlogPost(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
    ]

    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=200, unique=True)
    author_name = models.CharField(
        max_length=100, default="Your Name", help_text="Name of the author to display"
    )
    content = models.TextField(help_text="HTML content with image references")
    summary = models.TextField(
        blank=True, help_text="Short description for meta tags and previews"
    )
    meta_description = models.CharField(
        max_length=800, blank=True, help_text="SEO meta description"
    )
    featured_image_path = models.CharField(
        max_length=200,
        blank=True,
        help_text="Path to featured image in static folder (e.g., 'blog/img1.jpg')",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    @property
    def is_published(self):
        return self.status == "published" and self.published_at is not None

    def get_title_en(self):
        parts = self.title.split("|`", 1)
        return parts[0].strip()

    def get_title_fr(self):
        parts = self.title.split("|`", 1)
        if len(parts) <= 1 or not parts[1].strip():
            return self.get_title_en()
        return parts[1].strip()

    def get_content_en(self):
        parts = self.content.split("|`", 1)
        return parts[0].strip()

    def get_content_fr(self):
        parts = self.content.split("|`", 1)
        if len(parts) <= 1 or not parts[1].strip():
            return self.get_content_en()
        return parts[1].strip()

    def get_summary_en(self):
        parts = self.summary.split("|`", 1)
        return parts[0].strip()

    def get_summary_fr(self):
        parts = self.summary.split("|`", 1)
        if len(parts) <= 1 or not parts[1].strip():
            return self.get_summary_en()
        return parts[1].strip()

    def get_meta_description_en(self):
        parts = self.meta_description.split("|`", 1)
        return parts[0].strip()

    def get_meta_description_fr(self):
        parts = self.meta_description.split("|`", 1)
        if len(parts) <= 1 or not parts[1].strip():
            return self.get_meta_description_en()
        return parts[1].strip()


class MileageEntry(models.Model):
    TRIP_PURPOSE_CHOICES = [
        ("CLIENT_VISIT", "Client Visit"),
        ("PROSPECTING", "Prospecting"),
        ("SUPPLIES", "Picking up Supplies"),
        ("SERVICE", "Service Call"),
        ("OTHER", "Other Business Purpose"),
    ]

    date = models.DateField()
    trip_purpose = models.CharField(max_length=20, choices=TRIP_PURPOSE_CHOICES)
    start_odometer = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MaxValueValidator(999999, message="Odometer reading cannot exceed 999,999")
        ],
    )
    end_odometer = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[
            MaxValueValidator(999999, message="Odometer reading cannot exceed 999,999")
        ],
    )
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Mileage Entry"
        verbose_name_plural = "Mileage Entries"

    def __str__(self):
        return f"{self.date} - {self.trip_purpose}"

    def clean(self):
        # Check if both odometer readings are provided
        if self.start_odometer is not None and self.end_odometer is not None:
            if self.end_odometer <= self.start_odometer:
                raise ValidationError(
                    {
                        "end_odometer": "End odometer reading must be greater than start odometer reading"
                    }
                )


class BusinessVisit(models.Model):
    VISIT_TYPE_CHOICES = [
        ("COLD_VISIT", "Cold Visit"),
        ("COLD_CALL", "Cold Call"),
        ("FOLLOW_UP", "Follow-up Visit"),
        ("NETWORKING", "Networking Event"),
        ("REFERRAL", "Referral Visit"),
        ("OTHER", "Other"),
    ]

    date = models.DateField()
    business_name = models.CharField(max_length=200)
    address = models.TextField()
    contact_person = models.CharField(max_length=100, blank=True)
    contact_position = models.CharField(max_length=100, blank=True)
    visit_type = models.CharField(max_length=20, choices=VISIT_TYPE_CHOICES)
    cards_left = models.PositiveIntegerField(default=1)
    notes = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Business Visit"
        verbose_name_plural = "Business Visits"

    def __str__(self):
        return f"{self.date} - {self.business_name}"


class FollowUp(models.Model):

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
    ]

    quote = models.ForeignKey(
        Quote,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="follow_ups",
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="follow_ups",
    )
    due_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date"]
        verbose_name = "Follow-up"
        verbose_name_plural = "Follow-ups"

    def __str__(self):
        entity = self.quote or self.client
        return f"{entity} ({self.due_date})"

    @property
    def is_overdue(self):
        from django.utils import timezone

        return self.due_date <= timezone.now().date() and self.status == "PENDING"
