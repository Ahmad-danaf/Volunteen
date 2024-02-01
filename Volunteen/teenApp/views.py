from email import message
from django.shortcuts import redirect, render

from .forms import CreateUserForm

from django.contrib.auth.models import auth


from django.contrib.auth.decorators import login_required


from django.contrib import messages

from django.shortcuts import render, redirect, get_object_or_404
from .models import Task
from .forms import TaskForm, UpdateTaskForm

# Create your views here.
def home(request):
    return redirect('two_factor:login')

def index(request):
    return render(request,'index.html')

def register(request):

    form = CreateUserForm()

    if request.method == 'POST':

        form = CreateUserForm(request.POST)

        if form.is_valid():

            form.save()

            return redirect("")


    context = {'form': form}

    return render(request, 'register.html', context=context)


def dashboard(request):

    return render(request, 'dashboard.html')
def list_view(request):
    tasks = Task.objects.filter(completed=False)
    return render(request, 'list_tasks.html', {'tasks': tasks})

def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('list')  # Replace 'list' with the actual name of your task list view
    else:
        form = TaskForm()

    return render(request, 'create_task.html', {'form': form})

def update_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)

    if request.method == 'POST':
        form = UpdateTaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('list')  # Replace 'list' with the actual name of your task list view
    else:
        form = UpdateTaskForm(instance=task)

    return render(request, 'update_task.html', {'form': form, 'task': task})

def delete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.delete()
    return redirect('list')  # Replace 'list' with the actual name of your task list view

def complete_task(request, task_id):
    task = get_object_or_404(Task, pk=task_id)
    task.completed = True
    task.save()
    return redirect('list')  # Replace 'list' with the actual name of your task list view
