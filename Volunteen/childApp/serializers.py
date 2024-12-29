from rest_framework import serializers
from .models import Child

class ChildSerializer(serializers.ModelSerializer):
    mentor_ids = serializers.PrimaryKeyRelatedField(
        many=True, read_only=True, source='mentors'
    )
    completed_task_titles = serializers.SerializerMethodField()

    class Meta:
        model = Child
        fields = [
            'id',
            'user',
            'mentor_ids',
            'points',
            'completed_task_titles',
            'identifier',
            'secret_code',
        ]

    def get_completed_task_titles(self, obj):
        return [task.title for task in obj.completed_tasks.all()]
