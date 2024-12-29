from rest_framework import serializers
from .models import Mentor
from childApp.serializers import ChildSerializer
from teenApp.serializers import TaskSerializer
from childApp.models import Child


class MentorSerializer(serializers.ModelSerializer):
    assigned_children = serializers.SerializerMethodField()

    class Meta:
        model = Mentor
        fields = [
            'id',
            'user',
            'assigned_children',
        ]

    def get_assigned_children(self, obj):
        
        children = Child.objects.filter(mentors=obj)
        return ChildSerializer(children, many=True).data
