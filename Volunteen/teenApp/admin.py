from django.contrib import admin
from .models import Task,Reward,Child,Mentor

# Register your models here.

admin.site.register(Task)
admin.site.register(Reward)
admin.site.register(Child)
admin.site.register(Mentor)