from django.shortcuts import render


def legal_notice(request):
    return render(request, "pages/legal_notice.html")


def privacy(request):
    return render(request, "pages/privacy.html")


def accessibility(request):
    return render(request, "pages/accessibility.html")


def contact(request):
    return render(request, "pages/contact.html")


def terms(request):
    return render(request, "pages/terms.html")
