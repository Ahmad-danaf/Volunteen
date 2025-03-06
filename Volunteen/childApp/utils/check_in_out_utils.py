
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from childApp.models import Child
from teenApp.entities.task import Task
from teenApp.entities.TaskCompletion import TaskCompletion

def process_check_in(child_id, task_id, image_data):
    """
    Background task that processes a check-in:
    - Reads the image bytes,
    - Saves the image via default_storage,
    - Updates (or creates) the TaskCompletion record.
    """
    child = Child.objects.get(id=child_id)
    task = get_object_or_404(Task, id=task_id)
    task_completion, created = TaskCompletion.objects.get_or_create(task=task, child=child)

    # Define the file path and create a ContentFile from the image bytes
    file_path = f'checkin_images/{child.id}_{task.id}_checkin.jpg'
    content_file = ContentFile(image_data, name=f'{child.id}_{task.id}_checkin.jpg')

    # Save the image and update the task_completion record
    saved_path = default_storage.save(file_path, content_file)
    task_completion.checkin_img = saved_path
    task_completion.status = 'checked_in'
    task_completion.save()
    return f"Check-in processed for child {child.user.username} on task {task.title}"

def process_check_out(child_id, task_id, image_data):
    """
    Background task that processes a check-out:
    - Reads the image bytes,
    - Checks that a check-in image exists,
    - Saves the checkout image,
    - Updates the TaskCompletion status.
    """
    child = Child.objects.get(id=child_id)
    task = get_object_or_404(Task, id=task_id)
    task_completion, created = TaskCompletion.objects.get_or_create(task=task, child=child)

    if not task_completion.checkin_img:
        return "Error: No check-in image found. Cannot process check-out."

    file_path = f'checkout_images/{child.id}_{task.id}_checkout.jpg'
    content_file = ContentFile(image_data, name=f'{child.id}_{task.id}_checkout.jpg')

    saved_path = default_storage.save(file_path, content_file)
    task_completion.checkout_img = saved_path
    task_completion.status = 'pending'
    task_completion.save()
    return f"Check-out processed for child {child.user.username} on task {task.title}"
