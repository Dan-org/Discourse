from models import Page
from django.shortcuts import render, get_object_or_404

def document(request, name="home"):
    page = get_object_or_404(Page, path=name)
    return render(request, 'page.html', locals())