# Volunteen Project
<img src="Volunteen/Volunteen/static/images/logo.png" alt="Volunteen Logo" width="300"/>

## Description
Welcome to Volunteen! This project, Volunteen, is a system we developed to manage tasks that increase the involvement of children and youth in community projects. Each positive task they complete earns them points that can be redeemed for rewards through partnerships with local businesses.

Volunteen is structured following Uncle Bob's Clean Architecture principles, organized into four distinct layers:

- **Entities:** The core business logic.
- **Use Cases:** Application-specific business rules.
- **Interface Adapters:** Converters that transform data from the use cases to a format that can be used by the framework.
- **Frameworks & Drivers:** External interfaces such as databases, web frameworks, or other I/O components.

Below are screenshots showcasing different aspects of the **Volunteen** system:

<img src="Volunteen/Volunteen/static/images/kids_portal.png" alt="Kids Portal" width="300"/>

**Screenshot of the Kids Portal, where children and youth can view and manage their tasks.**

<img src="Volunteen/Volunteen/static/images/mentor_portal.png" alt="Mentor Portal" width="300"/>

**Screenshot of the Mentor Portal, where mentors can assign tasks and track progress.**

<img src="Volunteen/Volunteen/static/images/shop_portal.png" alt="Shop Portal" width="300"/>

**Screenshot of the Shop Portal, where points can be redeemed for rewards.**

## Installation
To install Volunteen, follow these steps:

1. Clone the repository: `git clone https://github.com/Ahmad-danaf/Volunteen`
2. Navigate to the project directory: `cd volunteen`
3. [Optional] Set up a virtual environment: `python -m venv venv` (optional but recommended)
4. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS and Linux: `source venv/bin/activate``
5. Install dependencies: `pip install -r requirements.txt`
   
## Structure
   ```bash
Volunteen/
├── Volunteen/                  # Main Django project folder
│   ├── frameworks_and_drivers/ # Project settings, URLs, etc.
│   ├── static/                 # Static files (CSS, JS, images)
│   ├── media/                  # Uploaded and default media
│   ├── db.sqlite3              # SQLite database (for development)
│   ├── constants.py            # Project-wide constants
│   └── manage.py               # Django project management script
│
├── childApp/                   # Child user functionality
├── mentorApp/                  # Mentor dashboard and views
├── parentApp/                  # Parent tools and task assignment
├── institutionApp/             # Institutional access and transfer tools
├── managementApp/              # Admin and donation management
├── shopApp/                    # Shop and reward redemption logic
├── teenApp/                    # Core business logic and clean architecture
│
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not committed)
└── README.md                   # Project overview (this file)



```

## Usage
To use Volunteen, follow these steps:

1. Apply database migrations:
   ```bash
   python manage.py migrate
   
2. Create a superuser account
   ```bash
   python manage.py createsuperuser
   ```
   Follow the prompts to set up your admin username and password.

3. Run the Django development server:
   ```bash
   python manage.py runserver
4. Open your web browser and navigate to http://127.0.0.1:8000/ to access the homepage.
5. Log in using the appropriate user credentials:
 - For children: use the credentials provided during registration.
 - For mentors: use the mentor credentials.
 - For shop owners: use the shop owner credentials.
6. Children can view and complete tasks assigned to them, earning points for each completed task.
7. Mentors can assign tasks to children and monitor their progress.
8. Shop owners can manage reward redemptions and track points used by children.
9. Use the admin panel to manage users, tasks, and rewards: http://127.0.0.1:8000/admin/


## Built With
- [Python](https://www.python.org/) - The programming language used.
- [Django](https://www.djangoproject.com/) - The web framework used.
- [SQLite](https://www.sqlite.org/index.html) - The database used.
- [HTML/CSS/JavaScript](https://developer.mozilla.org/en-US/docs/Learn/Getting_started_with_the_web/HTML_basics) - For the frontend components.
- [Bootstrap](https://getbootstrap.com/) - For responsive design and styling.
- [Git](https://git-scm.com/) - Version control system.
- [AWS](https://aws.amazon.com/) - Used for deployment.
- 
## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

