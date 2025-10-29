from django.shortcuts import render

def admin_dashboard(request):
    return render(request, 'admin/index.html')

def frontend_home(request):
    return render(request, 'frontend/index.html')
