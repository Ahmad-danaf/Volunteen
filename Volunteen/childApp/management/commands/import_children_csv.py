import csv
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from childApp.models import Child
from mentorApp.models import Mentor
from institutionApp.models import Institution
from django.db import transaction

class Command(BaseCommand):
    help = "Import children from a CSV file with columns: username,password,identifier,secret_code,mentor,institution,city"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help="Path to the CSV file")

    @transaction.atomic
    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        self.stdout.write("############# Starting children import ##############")
        
        users_created = 0
        users_skipped = 0
        children_created = 0
        children_skipped = 0
        errors = 0
        row_count = 0
        
        try:
            with open(csv_file, newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row_num, row in enumerate(reader, start=2):  # row_num starts at 2 to account for header row
                    try:
                        row_count += 1
                        username = row['username'].strip()
                        password = row['password'].strip()
                        identifier = row['identifier'].strip().zfill(5)
                        secret_code = row['secret_code'].strip()
                        mentor_username = row['mentor'].strip()
                        institution_name = row['institution'].strip()
                        city = row['city'].strip() or "TLV"
                        
                        self.stdout.write(f"\nProcessing row {row_num}: {username}")
                        
                        # Create or get the user (child user)
                        user, user_created = User.objects.get_or_create(username=username, defaults={
                            'email': '',  # email not provided in CSV
                            'first_name': '',
                            'last_name': ''
                        })
                        if user_created:
                            user.set_password(password)
                            user.save()
                            users_created += 1
                            self.stdout.write(f"  - User created: {username}")
                        else:
                            users_skipped += 1
                            self.stdout.write(f"  - User already exists: {username}")
                        
                        # Get the institution by name if provided
                        institution = None
                        if institution_name:
                            institution = Institution.objects.filter(name=institution_name).first()
                            if institution:
                                self.stdout.write(f"  - Found institution: {institution_name}")
                            else:
                                self.stdout.write(f"  - Institution not found: {institution_name}")
                        
                        # Create or get the child record
                        child, child_created = Child.objects.get_or_create(user=user, defaults={
                            'identifier': identifier,
                            'secret_code': secret_code,
                            'institution': institution,
                            'city': city
                        })
                        if child_created:
                            children_created += 1
                            self.stdout.write(f"  - Child created for user: {username}")
                        else:
                            children_skipped += 1
                            self.stdout.write(f"  - Child already exists for user: {username}")
                        
                        # Associate mentor if provided
                        if mentor_username:
                            mentor = Mentor.objects.filter(user__username=mentor_username).first()
                            if mentor:
                                child.mentors.add(mentor)
                                self.stdout.write(f"  - Added mentor: {mentor_username}")
                            else:
                                self.stdout.write(f"  - Mentor not found: {mentor_username}")
                    
                    except Exception as e:
                        errors += 1
                        self.stdout.write(f"[Row {row_num}] Error: {e}")
                        
        except FileNotFoundError:
            self.stdout.write(f"File not found: {csv_file}")
            return
        
        # Print summary
        self.stdout.write("\n=== Import Summary ===")
        self.stdout.write(f"Users created: {users_created}")
        self.stdout.write(f"Users skipped (already existed): {users_skipped}")
        self.stdout.write(f"Children created: {children_created}")
        self.stdout.write(f"Children skipped (already existed): {children_skipped}")
        self.stdout.write(f"Errors encountered: {errors}")
        self.stdout.write(f"Total rows processed: {row_count}")
        self.stdout.write("############# Children import completed ##############")
