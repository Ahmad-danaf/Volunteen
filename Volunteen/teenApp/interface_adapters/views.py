from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from django.contrib.auth import logout
from teenApp.entities.task import Task
from django.urls import reverse
from rest_framework.permissions import AllowAny


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Handle user logout."""
        logout(request)
        return Response({'message': 'Logged out successfully.'}, status=200)


class LandingPageView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def get(self, request):
        """Render landing page content."""
        return Response({'message': 'Welcome to TeenApp!'}, status=200)

class HomeRedirectView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Redirect users based on their group."""
        if request.user.groups.filter(name='Children').exists():
            redirect_url = reverse('childApp:child_home')
        elif request.user.groups.filter(name='Mentors').exists():
            redirect_url = reverse('mentorApp:mentor_home')
        elif request.user.groups.filter(name='Shops').exists():
            redirect_url = reverse('shopApp:shop_home')
        else:
            #return redirect('/admin')
            redirect_url = reverse('admin:index')
        
        return Response({'redirect_url': redirect_url}, status=200)
    
class DefaultHomeView(APIView):
    def get(self, request):
        """Default home view."""
        return Response({'message': 'Default Home Page'}, status=200)


class TaskListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """List all tasks."""
        tasks = Task.objects.all()
        task_data = [
            {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'deadline': task.deadline,
                'completed': task.completed,
                'points': task.points
            }
            for task in tasks
        ]
        return Response({'tasks': task_data}, status=200)
