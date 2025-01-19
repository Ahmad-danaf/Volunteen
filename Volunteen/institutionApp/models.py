from django.db import models

class Institution(models.Model):
    name = models.CharField(max_length=255, verbose_name='Institution Name')
    address = models.TextField(blank=True, null=True, verbose_name='Address')
    mentors = models.ManyToManyField('mentorApp.Mentor', related_name='institutions', verbose_name='Mentors')

    def get_children(self):
        """
        Returns all children in this institution through its mentors.
        """
        children = set()
        for mentor in self.mentors.all():
            children.update(mentor.children.all())  # Accessing related children from Mentor
        return children

    def __str__(self):
        return self.name
