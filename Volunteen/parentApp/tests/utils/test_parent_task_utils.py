from django.test import TestCase
from django.contrib.auth.models import User
from parentApp.utils.ParentTaskUtils import ParentTaskUtils
from parentApp.models import Parent
from teenApp.entities.TaskCompletion import TaskCompletion
from teenApp.entities.TaskAssignment import TaskAssignment
from teenApp.entities.task import Task
from childApp.models import Child
from datetime import datetime, timedelta

class ParentTaskUtilsTestCase(TestCase):
    def setUp(self):
        # Create test users
        self.parent_user = User.objects.create_user(
            username='parent_user',
            password='testpass123'
        )
        self.mentor_user = User.objects.create_user(
            username='mentor_user',
            password='testpass123'
        )
        self.child_user = User.objects.create_user(
            username='child_user',
            password='testpass123'
        )
        
        # Create parent
        self.parent = Parent.objects.create(
            user=self.parent_user,
            available_teencoins=100
        )
        
        # Create child
        self.child = Child.objects.create(
            user=self.child_user,
            parent=self.parent,
            points=0,
            identifier='CH001',
            secret_code='123'
        )
        
        # Create tasks
        self.task1 = Task.objects.create(
            title='Task 1',
            description='Description 1',
            points=10,
            deadline=datetime.now().date() + timedelta(days=7))
        
        self.task2 = Task.objects.create(
            title='Task 2',
            description='Description 2',
            points=20,
            deadline=datetime.now().date() + timedelta(days=14))
        
        # Create completed task
        self.completed_task = Task.objects.create(
            title='Completed Task',
            description='Completed Description',
            points=15,
            deadline=datetime.now().date() - timedelta(days=1))
        
        # Create task assignments - one parent assignment and one mentor assignment
        self.parent_assignment = TaskAssignment.objects.create(
            task=self.task1,
            child=self.child,
            assigned_by=self.parent_user
        )
        
        self.mentor_assignment = TaskAssignment.objects.create(
            task=self.task2,
            child=self.child,
            assigned_by=self.mentor_user
        )
        
        # Create completed task assignment
        self.completed_assignment = TaskAssignment.objects.create(
            task=self.completed_task,
            child=self.child,
            assigned_by=self.parent_user
        )
        
        # Create task completion for the completed task
        self.task_completion = TaskCompletion.objects.create(
            child=self.child,
            task=self.completed_task,
            status='approved'
        )

    def test_get_children(self):
        """Test that get_children returns all children belonging to the parent"""
        children = ParentTaskUtils.get_children(self.parent)
        self.assertEqual(children.count(), 1)
        self.assertEqual(children.first(), self.child)
        
        # Add another child
        child2 = Child.objects.create(
            user=User.objects.create_user(username='child2', password='testpass123'),
            parent=self.parent,
            points=0,
            identifier='CH002',
            secret_code='456'
        )
        children = ParentTaskUtils.get_children(self.parent)
        self.assertEqual(children.count(), 2)
        self.assertIn(self.child, children)
        self.assertIn(child2, children)

    def test_get_tasks_assigned_by_parent(self):
        """Test that get_tasks_assigned_by_parent returns only tasks assigned by the parent"""
        assignments = ParentTaskUtils.get_tasks_assigned_by_parent(self.parent)
        self.assertEqual(assignments.count(), 2)  # One regular and one completed task assignment
        self.assertIn(self.parent_assignment, assignments)
        self.assertIn(self.completed_assignment, assignments)
        self.assertNotIn(self.mentor_assignment, assignments)

    def test_get_tasks_assigned_by_mentors_for_parent_children(self):
        """Test that get_tasks_assigned_by_mentors_for_parent_children returns only mentor-assigned tasks"""
        assignments = ParentTaskUtils.get_tasks_assigned_by_mentors_for_parent_children(self.parent)
        self.assertEqual(assignments.count(), 1)
        self.assertEqual(assignments.first(), self.mentor_assignment)
        self.assertNotIn(self.parent_assignment, assignments)
        self.assertNotIn(self.completed_assignment, assignments)

    def test_assign_task_to_child_valid(self):
        """Test assigning a task to a valid child (child belongs to parent)"""
        new_task = Task.objects.create(
            title='New Task',
            description='New Description',
            points=5,
            deadline=datetime.now().date() + timedelta(days=3))
        
        assignment = ParentTaskUtils.assign_task_to_child(self.parent, new_task, self.child)
        self.assertIsInstance(assignment, TaskAssignment)
        self.assertEqual(assignment.task, new_task)
        self.assertEqual(assignment.child, self.child)
        
        # Verify the assignment exists in the database
        db_assignment = TaskAssignment.objects.get(task=new_task, child=self.child)
        self.assertEqual(db_assignment.assigned_by, self.parent.user)

    def test_assign_task_to_child_invalid(self):
        """Test assigning a task to a child that doesn't belong to the parent"""
        other_parent = Parent.objects.create(
            user=User.objects.create_user(username='other_parent', password='testpass123'),
            available_teencoins=50
        )
        other_child = Child.objects.create(
            user=User.objects.create_user(username='other_child', password='testpass123'),
            parent=other_parent,
            points=0,
            identifier='CH003',
            secret_code='789'
        )
        
        with self.assertRaises(ValueError) as context:
            ParentTaskUtils.assign_task_to_child(self.parent, self.task1, other_child)
        
        self.assertEqual(str(context.exception), "This child does not belong to the current parent.")

    def test_create_and_assign_task_success(self):
        """Test successfully creating and assigning a new task"""
        initial_coins = self.parent.available_teencoins
        selected_children = [self.child.id]
        
        task, assignments = ParentTaskUtils.create_and_assign_task(
            parent=self.parent,
            name='New Created Task',
            description='New Created Description',
            points=30,
            due_date=(datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            selected_children=selected_children
        )
        
        # Verify the task was created
        self.assertIsInstance(task, Task)
        self.assertEqual(task.title, 'New Created Task')
        self.assertEqual(task.points, 30)
        
        # Verify the assignment was created
        self.assertEqual(len(assignments), 1)
        self.assertEqual(assignments[0].child, self.child)
        
        # Verify parent's teencoins were deducted
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.available_teencoins, initial_coins - 30)
        
        # Verify the assignment exists in the database
        db_assignment = TaskAssignment.objects.get(task=task, child=self.child)
        self.assertEqual(db_assignment.assigned_by, self.parent.user)

    def test_create_and_assign_task_insufficient_coins(self):
        """Test creating a task with insufficient teencoins raises an error"""
        self.parent.available_teencoins = 10
        self.parent.save()
        
        with self.assertRaises(ValueError) as context:
            ParentTaskUtils.create_and_assign_task(
                parent=self.parent,
                name='Expensive Task',
                description='Should fail',
                points=20,  # More than available
                due_date=(datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
                selected_children=[self.child.id]
            )
        
        self.assertEqual(str(context.exception), "Insufficient teencoins to assign this task.")
        
        # Verify no task was created
        self.assertFalse(Task.objects.filter(title='Expensive Task').exists())
        
        # Verify no coins were deducted
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.available_teencoins, 10)

    def test_create_and_assign_task_multiple_children(self):
        """Test creating a task and assigning it to multiple children"""
        # Create another child for the parent
        child2 = Child.objects.create(
            user=User.objects.create_user(username='child2', password='testpass123'),
            parent=self.parent,
            points=0,
            identifier='CH002',
            secret_code='456'
        )
        
        initial_coins = self.parent.available_teencoins
        selected_children = [self.child.id, child2.id]
        
        task, assignments = ParentTaskUtils.create_and_assign_task(
            parent=self.parent,
            name='Multi-child Task',
            description='Assigned to multiple children',
            points=15,
            due_date=(datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
            selected_children=selected_children
        )
        
        # Verify the task was created
        self.assertIsInstance(task, Task)
        
        # Verify both assignments were created
        self.assertEqual(len(assignments), 2)
        assigned_children = {a.child for a in assignments}
        self.assertEqual(assigned_children, {self.child, child2})
        
        # Verify parent's teencoins were deducted correctly (15 points × 2 children)
        self.parent.refresh_from_db()
        self.assertEqual(self.parent.available_teencoins, initial_coins - 30)
        
        # Verify assignments exist in the database
        self.assertEqual(TaskAssignment.objects.filter(task=task).count(), 2)

    def test_get_assigned_tasks_count(self):
        """Test getting the count of tasks assigned to a child by the parent"""
        # Initial count should be 2 (from setUp - self.parent_assignment and self.completed_assignment)
        count = ParentTaskUtils.get_assigned_tasks_count(self.child)
        self.assertEqual(count, 2)
        
        # Add another assignment
        new_task = Task.objects.create(
            title='Additional Task',
            description='Additional Description',
            points=5,
            deadline=datetime.now().date() + timedelta(days=1))
        
        TaskAssignment.objects.create(
            task=new_task,
            child=self.child,
            assigned_by=self.parent_user
        )
        
        count = ParentTaskUtils.get_assigned_tasks_count(self.child)
        self.assertEqual(count, 3)
        
        # Add an assignment by someone else shouldn't count
        another_task = Task.objects.create(
            title='Another Task',
            description='Another Description',
            points=7,
            deadline=datetime.now().date() + timedelta(days=2))
            
        TaskAssignment.objects.create(
            task=another_task,
            child=self.child,
            assigned_by=self.mentor_user
        )
        
        count = ParentTaskUtils.get_assigned_tasks_count(self.child)
        self.assertEqual(count, 3)

    def test_get_completed_tasks_count(self):
        """Test getting the count of completed tasks assigned by the parent"""
        # Initial count should be 1 (from setUp)
        count = ParentTaskUtils.get_completed_tasks_count(self.child)
        self.assertEqual(count, 1)
        
        # Add another completed task
        new_task = Task.objects.create(
            title='New Completed Task',
            description='New Completed Description',
            points=10,
            deadline=datetime.now().date() - timedelta(days=2))
        
        assignment = TaskAssignment.objects.create(
            task=new_task,
            child=self.child,
            assigned_by=self.parent_user
        )
        
        TaskCompletion.objects.create(
            child=self.child,
            task=new_task,
            status='approved'
        )
        
        count = ParentTaskUtils.get_completed_tasks_count(self.child)
        self.assertEqual(count, 2)
        
        # Add a non-approved completion shouldn't count
        new_task2 = Task.objects.create(
            title='Pending Task',
            description='Pending Description',
            points=5,
            deadline=datetime.now().date() - timedelta(days=1))
        
        assignment2 = TaskAssignment.objects.create(
            task=new_task2,
            child=self.child,
            assigned_by=self.parent_user
        )
        
        TaskCompletion.objects.create(
            child=self.child,
            task=new_task2,
            status='pending'
        )
        
        count = ParentTaskUtils.get_completed_tasks_count(self.child)
        self.assertEqual(count, 2)
        
        # Add a completion for a mentor-assigned task shouldn't count
        mentor_task = Task.objects.create(
            title='Mentor Task',
            description='Mentor Description',
            points=15,
            deadline=datetime.now().date() - timedelta(days=3))
        
        mentor_assignment = TaskAssignment.objects.create(
            task=mentor_task,
            child=self.child,
            assigned_by=self.mentor_user
        )
        
        TaskCompletion.objects.create(
            child=self.child,
            task=mentor_task,
            status='approved'
        )
        
        count = ParentTaskUtils.get_completed_tasks_count(self.child)
        self.assertEqual(count, 2)