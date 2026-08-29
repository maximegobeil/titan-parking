from django.contrib import admin
from django.urls import path

from . import views  # Import views from the main project

urlpatterns = [
    path("", views.home_view, name="home"),
    path("terms-of-service/", views.terms_view, name="terms-of-service"),
    path("privacy-policy/", views.privacy_view, name="privacy-policy"),
    path("sitemap.xml", views.sitemap_view, name="sitemap"),
    path("robots.txt", views.robots_view, name="robots"),
    path("submit-contact/", views.submit_contact, name="submit_contact"),
    path("blog/", views.blog_list, name="blog"),
    path("blog/search/", views.blog_search, name="blog_search"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("a-propos/", views.about_view, name="about-us"),
    # Temporary invoice url
    path("invoice/<int:pk>/", views.invoice_view_pdf, name="invoice_pdf"),
    path("invoice-html/<int:pk>/", views.invoice_view_html, name="invoice_html"),
    path("terms-pdf/", views.terms_view_pdf, name="terms_pdf"),
    path("quote-calculator/", views.quote_calculator_view, name="quote_calculator"),
    path(
        "angle-parking-calculator/",
        views.angle_parking_calculator_view,
        name="angle_parking_calculator",
    ),
    path("client-pdf/<str:access_token>/", views.client_pdf, name="client_pdf"),
    # Services
    path(
        "marquage-de-stationnement/",
        views.parking_lot_striping_view,
        name="parking-lot-striping",
    ),
    path("marquage-interieur/", views.indoor_markings_view, name="indoor-markings"),
    path(
        "marquage-au-sol/",
        views.pavement_markings_view,
        name="pavement-markings",
    ),
    path(
        "marquage-personnalise/",
        views.custom_layout_design_view,
        name="custom-layout-design",
    ),
    path(
        "restauration-de-lignes/",
        views.line_restoration_view,
        name="line-restoration",
    ),
    path("jeux-exterieurs/", views.playground_view, name="playground"),
]
