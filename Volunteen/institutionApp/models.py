
from django.db import models
from django.contrib.auth.models import User
from mentorApp.models import Mentor
from django.utils.timezone import now
from django.contrib.auth.models import Group

class Institution(models.Model):
    name = models.CharField(max_length=255, unique=True, verbose_name="Institution Name")
    manager = models.OneToOneField(User, on_delete=models.CASCADE, related_name='institution', verbose_name="Institution Manager", null=True, blank=True)
    address = models.TextField(blank=True, null=True, verbose_name='Address')

    # Total Teencoins purchased by the institution (sum of all purchases)
    total_teencoins = models.IntegerField(default=0, verbose_name="Total Teencoins")

    # Available Teencoins that can be allocated to mentors (like a bank balance)
    available_teencoins = models.IntegerField(default=0, verbose_name="Available Teencoins")

    # Mentors associated with this institution
    mentors = models.ManyToManyField(Mentor, related_name="institutions", blank=True, verbose_name="Mentors")

    def __str__(self):
        return self.name

    def allocate_teencoins_to_mentor(self, mentor, amount):
        """
        Allocates Teencoins from the institution to a mentor.
        Ensures that the allocation does not exceed the available balance.
        """
        if amount > self.available_teencoins:
            raise ValueError("Not enough available Teencoins.")
        
        mentor.available_teencoins += amount
        self.available_teencoins -= amount
        mentor.save()
        self.save()

    def purchase_teencoins(self, amount):
        """
        Adds Teencoins to the institution's total balance.
        """
        self.total_teencoins += amount
        self.available_teencoins += amount
        self.save()

    def track_mentor_usage(self):
        """
        Returns a dictionary showing the Teencoins allocated and available for each mentor.
        """
        data = {}
        for mentor in self.mentors.all():
            assigned_teencoins = mentor.get_assigned_teencoins()
            transferred_teencoins = mentor.get_transferred_teencoins()

            data[mentor.user.username] = {
                "Assigned Teencoins": assigned_teencoins,  # Teencoins allocated to tasks but not yet completed
                "Transferred Teencoins": transferred_teencoins,  # Teencoins transferred after task approval
                "Available Teencoins": mentor.available_teencoins,  # Teencoins still available for allocation
            }
        return data
    
    def save(self, *args, **kwargs):
        """
        Automatically add the child to the 'Children' group if not already added.
        """
        super().save(*args, **kwargs)
        institutions_group, created = Group.objects.get_or_create(name='Institutions')
        self.manager.groups.add(institutions_group)


class TeencoinsTransfer(models.Model):
    institution = models.ForeignKey(Institution, on_delete=models.CASCADE, related_name='transfers')
    sender = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='sent_transfers', null=True, blank=True)
    receiver = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='received_transfers')
    amount = models.PositiveIntegerField()
    timestamp = models.DateTimeField(default=now)

    def __str__(self):
        sender_name = self.sender.user.username if self.sender else "Institution"
        return f"{sender_name} → {self.receiver.user.username}: {self.amount} Teencoins"
