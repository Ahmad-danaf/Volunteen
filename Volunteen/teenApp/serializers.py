from rest_framework import serializers
from teenApp.entities.task import Task
from teenApp.entities.TaskCompletion import TaskCompletion
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone']
        
        
class TaskSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id', 'description', 'deadline', 'completed', 'title', 'img', 
            'points', 'additional_details', 'assigned_children', 
            'assigned_mentors', 'new_task', 'viewed', 'total_bonus_points', 
            'completed_date', 'admin_max_points', 'duration', 'is_overdue'
        ]

class TaskCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCompletion
        fields = ['id', 'child', 'task', 'completion_date', 'bonus_points']
