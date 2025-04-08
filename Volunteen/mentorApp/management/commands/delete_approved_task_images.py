from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
import os
from datetime import datetime

from teenApp.entities.TaskCompletion import TaskCompletion  # Update this import path if needed


class Command(BaseCommand):
    help = 'Delete check-in and check-out images for all approved task completions'

    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(f"[{start_time}] Starting image cleanup process for approved task completions")
        
        # Find all task completions with 'approved' status that have images
        task_completions = TaskCompletion.objects.filter(
            status='approved'
        ).filter(
            Q(checkin_img__isnull=False) | Q(checkout_img__isnull=False)
        )
        
        total_count = task_completions.count()
        self.stdout.write(f"Found {total_count} approved task completions with images to process")
        
        # Initialize counters
        processed_count = 0
        checkin_deleted_count = 0
        checkout_deleted_count = 0
        error_count = 0
        
        # Process each task completion
        for completion in task_completions:
            processed_count += 1
            
            # Handle check-in image
            if completion.checkin_img:
                try:
                    image_path = completion.checkin_img.path
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        checkin_deleted_count += 1
                    completion.checkin_img = None
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f"Error processing task completion ID {completion.id}: {e}"))
            
            # Handle check-out image
            if completion.checkout_img:
                try:
                    image_path = completion.checkout_img.path
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        checkout_deleted_count += 1
                    completion.checkout_img = None
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.ERROR(f"Error processing task completion ID {completion.id}: {e}"))
                    
            # Save the model with the cleared image fields
            completion.save(update_fields=['checkin_img', 'checkout_img'])
            
            # Log progress at regular intervals
            if processed_count % 100 == 0 or processed_count == total_count:
                self.stdout.write(f"Progress: {processed_count}/{total_count} task completions processed ({(processed_count/total_count)*100:.1f}%)")
        
        # Calculate timing
        end_time = timezone.now()
        duration = end_time - start_time
        
        # Final summary report
        self.stdout.write(self.style.SUCCESS(f"""
========== CLEANUP SUMMARY ==========
Time started:           {start_time}
Time completed:         {end_time}
Total duration:         {duration.total_seconds():.2f} seconds

Task completions found: {total_count}
Task completions processed: {processed_count}
Check-in images deleted: {checkin_deleted_count}
Check-out images deleted: {checkout_deleted_count}
Total images deleted:   {checkin_deleted_count + checkout_deleted_count}
Errors encountered:     {error_count}
=======================================
        """))