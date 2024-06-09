# teenApp/use_cases/assign_bonus_points.py

from teenApp.interface_adapters.repositories import ChildRepository, TaskRepository,MentorRepository

class AssignBonusPoints:
    def __init__(self, child_repository: ChildRepository, task_repository: TaskRepository, mentor_repository: MentorRepository):
        self.child_repository = child_repository
        self.task_repository = task_repository
        self.mentor_repository = mentor_repository

    def execute(self, task_id, child_id, mentor_id, bonus_points):
        if bonus_points > 10:
            raise ValueError("Cannot assign more than 10 bonus points at a time.")

        child = self.child_repository.get_child_by_id(child_id)
        task = self.task_repository.get_task_by_id(task_id)
        mentor = self.mentor_repository.get_mentor_by_id(mentor_id)
        task
        # Ensure the mentor is mentoring the child
        if mentor not in child.mentors.all():
            raise ValueError("Mentor is not assigned to this child")

        if task.total_bonus_points + bonus_points > task.admin_max_points:
            raise ValueError("Total bonus points for this task cannot exceed max points.")

        # Add bonus points to the child's total
        child.add_points(bonus_points)
        child.save()

        # Add bonus points to the task's total bonus points
        task.total_bonus_points += bonus_points
        task.save()

        # Mark the task as completed for the child
        child.completed_tasks.add(task)
        child.save()