from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from parentApp.models import Parent

@login_required
def parent_home(request):
    try:
        parent = Parent.objects.get(user=request.user)
    except Parent.DoesNotExist:
        return HttpResponse("Parent not found")

    children = parent.children.all()  # Retrieve all children associated with the parent
    total_points = sum(child.points for child in children)
    child_details = [
        {
            'name': f"{child.user.first_name} {child.user.last_name}",
            'points': child.points,
            'level': child.level,
            'identifier': child.identifier,
        }
        for child in children
    ]

    context = {
        'parent': parent,
        'children': child_details,
        'total_points': total_points,
    }

    return render(request, 'parent_home.html', context)
