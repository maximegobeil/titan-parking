import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from .forms import ContactForm
from .models import BlogPost, Quote, QuoteVisit


def home_view(request):
    return render(request, "pages/index.html", {"form": ContactForm()})


def about_view(request):
    return render(request, "pages/about.html")


def page_not_found_view(request, exception=None):
    return render(request, "pages/404.html", status=404)


@login_required
def terms_view(request):
    return render(request, "pages/terms-of-service.html")


def privacy_view(request):
    return render(request, "pages/privacy-policy.html")


def sitemap_view(request):
    blog_posts = BlogPost.objects.filter(status="published", published_at__isnull=False)

    return render(
        request,
        "sitemap.xml",
        {
            "blog_posts": blog_posts,
        },
        content_type="application/xml",
    )


def robots_view(request):
    return render(request, "robots.txt", content_type="text/plain")


def submit_contact(request):
    """View to handle contact form submission"""
    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            # Get cleaned data
            name = form.cleaned_data["name"]
            email = form.cleaned_data["email"]
            phone = form.cleaned_data["phone"]
            service = form.cleaned_data["service"]
            message_content = form.cleaned_data["message"]

            # Get service display name
            service_display = dict(form.fields["service"].choices)[service]

            # Create email content
            subject = f"New Quote Request: {service_display}"
            email_body = f"""
            New quote request from the website:
            
            Name: {name}
            Email: {email}
            Phone: {phone}
            Service: {service_display}
            
            Message:
            {message_content}
            """

            try:
                send_mail(
                    subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.EMAIL_HOST_USER],
                    fail_silently=False,
                )
                # Return success message for HTMX
                return render(request, "partials/home/contact-success.html")
            except Exception as e:
                # Handle email sending error
                return render(request, "partials/home/error-message.html")
        else:
            # Form is not valid, return errors
            return render(request, "partials/home/form-errors.html", {"form": form})

    # If not a POST request, return an empty response
    return HttpResponse("")


@login_required
def invoice_view_pdf(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related("client").prefetch_related("items__service"),
        id=pk,
    )

    image_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "templates",
        "quotes",
        "pdf",
        "assets",
        "invoice-header.png",
    )
    # Read CSS
    css_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "templates",
        "quotes",
        "pdf",
        "assets",
        "quote_template.css",
    )

    import base64

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    with open(css_path) as f:
        css_data = f.read()

    context = {
        "image_data": image_data,
        "css_data": css_data,
        "quote": quote,
    }

    # Render HTML content
    html_string = render_to_string("quotes/pdf/quote_template.html", context)

    # Create PDF response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="quote.pdf"'

    # Generate PDF
    HTML(string=html_string).write_pdf(response)

    return response


@login_required
def invoice_view_html(request, pk):
    quote = get_object_or_404(
        Quote.objects.select_related("client").prefetch_related("items__service"),
        id=pk,
    )

    image_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "templates",
        "quotes",
        "pdf",
        "assets",
        "invoice-header.png",
    )
    # Read CSS
    css_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "templates",
        "quotes",
        "pdf",
        "assets",
        "quote_template.css",
    )

    import base64

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    with open(css_path) as f:
        css_data = f.read()

    context = {
        "image_data": image_data,
        "css_data": css_data,
        "quote": quote,
    }

    return render(request, "quotes/pdf/quote_template.html", context)


@login_required
def terms_view_pdf(request):
    # Read CSS
    css_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "templates",
        "quotes",
        "pdf",
        "assets",
        "legal.css",
    )
    base_css_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "static",
        "css",
        "base.css",
    )

    with open(css_path) as f:
        css_data = f.read()

    with open(base_css_path) as f:
        base_css_data = f.read()

    context = {
        "css_data": f"{base_css_data}\n{css_data}",
    }

    # Render HTML content
    html_string = render_to_string("partials/terms/terms-pdf.html", context)

    # Create PDF response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'inline; filename="terms.pdf"'

    # Generate PDF
    HTML(string=html_string).write_pdf(response)

    return response


def blog_list(request):
    posts = BlogPost.objects.filter(status="published").order_by("-published_at")

    featured_post = None
    other_posts = []

    if posts.exists():
        featured_post = posts.first()
        other_posts = posts[1:]

    popular_posts = BlogPost.objects.filter(status="published").order_by(
        "-published_at"
    )[:5]

    return render(
        request,
        "pages/blog.html",
        {
            "featured_post": featured_post,
            "other_posts": other_posts,
            "popular_posts": popular_posts,
        },
    )


def blog_search(request):
    query = request.GET.get("q", "")

    if query:
        results = BlogPost.objects.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(summary__icontains=query),
            status="published",
        ).order_by("-published_at")
    else:
        results = []

    popular_posts = BlogPost.objects.filter(status="published").order_by(
        "-published_at"
    )[:5]

    return render(
        request,
        "pages/blog-search.html",
        {
            "query": query,
            "results": results,
            "popular_posts": popular_posts,
        },
    )


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, status="published")

    next_post = (
        BlogPost.objects.filter(published_at__gt=post.published_at, status="published")
        .order_by("published_at")
        .first()
    )

    prev_post = (
        BlogPost.objects.filter(published_at__lt=post.published_at, status="published")
        .order_by("-published_at")
        .first()
    )

    # Get related posts - for now, just get recent posts
    related_posts = (
        BlogPost.objects.filter(status="published")
        .exclude(id=post.id)
        .order_by("-published_at")[:2]
    )

    popular_posts = (
        BlogPost.objects.filter(status="published")
        .exclude(id=post.id)
        .order_by("-published_at")[:5]
    )

    return render(
        request,
        "pages/blog-detail.html",
        {
            "post": post,
            "next_post": next_post,
            "prev_post": prev_post,
            "related_posts": related_posts,
            "popular_posts": popular_posts,
        },
    )


@login_required
def quote_calculator_view(request):
    return render(request, "pages/quote-calculator.html")


@login_required
def angle_parking_calculator_view(request):
    return render(request, "pages/angle-parking-calculator.html")


def client_pdf(request, access_token):
    quote = get_object_or_404(Quote, access_token=access_token)

    if not quote.is_invoice and quote.expires_at < timezone.now():
        return render(
            request,
            "quotes/pdf/quote_expired.html",
            {"quote": quote, "expired_date": quote.expires_at},
        )

    # Log every visit regardless of timing
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    QuoteVisit.objects.create(
        quote=quote,
        ip_address=ip,
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )

    # Only flip status once the quote has been sent for at least 30 seconds
    # (filters out email-preview bots that hit the link immediately)
    BOT_GRACE_SECONDS = 30
    past_grace = (
        quote.sent_at is not None
        and (timezone.now() - quote.sent_at).total_seconds() >= BOT_GRACE_SECONDS
    )
    if past_grace:
        if quote.status == "sent":
            quote.status = "quote_viewed"
            quote.save()
        elif quote.status == "invoice":
            quote.status = "invoice_viewed"
            quote.save()

    image_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "templates",
        "quotes",
        "pdf",
        "assets",
        "invoice-header.png",
    )
    # Read CSS
    css_path = os.path.join(
        settings.BASE_DIR,
        "quotes",
        "templates",
        "quotes",
        "pdf",
        "assets",
        "quote_template.css",
    )

    import base64

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()

    with open(css_path) as f:
        css_data = f.read()

    context = {
        "image_data": image_data,
        "css_data": css_data,
        "quote": quote,
    }

    # Render HTML content
    html_string = render_to_string("quotes/pdf/quote_template.html", context)

    if quote.is_invoice:
        filename = f"facture-{quote.invoice_number}.pdf"
    else:
        filename = f"soumission-{quote.invoice_number}.pdf"

    # Create PDF response
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{filename}"'

    response["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"

    # Generate PDF
    HTML(string=html_string).write_pdf(response)

    return response


def parking_lot_striping_view(request):
    return render(request, "pages/services/parking-lot-striping.html")


def indoor_markings_view(request):
    return render(request, "pages/services/indoor-markings.html")


def pavement_markings_view(request):
    return render(request, "pages/services/pavement-markings.html")


def custom_layout_design_view(request):
    return render(request, "pages/services/custom-layout-design.html")


def line_restoration_view(request):
    return render(request, "pages/services/line-restoration.html")


def playground_view(request):
    return render(request, "pages/services/playground.html")
