from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Report
from .forms import ReportForm

@login_required
def create_report(request):
    if request.user.role != 'Admin':
        messages.error(request, "Only administrators can create reports")
        return redirect('home')
    
    if request.method == 'POST':
        form = ReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.admin = request.user
            report.save()
            messages.success(request, "Report created successfully!")
            return redirect('report-list')
    else:
        form = ReportForm()
    
    return render(request, 'reports/create.html', {'form': form})

@login_required
def report_list(request):
    if request.user.role != 'Admin':
        messages.error(request, "Only administrators can view reports")
        return redirect('home')
    
    reports = Report.objects.filter(admin=request.user).order_by('-generated_at')
    return render(request, 'reports/list.html', {'reports': reports})