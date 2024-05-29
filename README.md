# Volunteen Project

## Description
Welcome to Volunteen! This project, Volunteen, is a system we developed to manage tasks that increase the involvement of children and youth in community projects. Each positive task they complete earns them points that can be redeemed for rewards through partnerships with local businesses. This README provides essential information for understanding the project.

## Installation
To install Volunteen, follow these steps:

1. Clone the repository: `git clone https://github.com/Ahmad-danaf/Volunteen`
2. Navigate to the project directory: `cd volunteen`
3. [Optional] Set up a virtual environment: `python -m venv venv` (optional but recommended)
4. Activate the virtual environment:
   - On Windows: `venv\Scripts\activate`
   - On macOS and Linux: `source venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt`
6. [Any additional installation steps, such as configuring environment variables]

## Structure
Volunteen/
│
├── README.md
├── requirements.txt
│
├── Volunteen/
│   ├── __pycache__/
│   ├── frameworks_and_drivers/
│   │   ├── __pycache__/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   │
│   ├── static/
│   │   ├── css/
│   │   │   ├── assign_task.css
│   │   │   ├── child_home.css
│   │   │   ├── list_tasks.css
│   │   │   ├── mentor_children_details.css
│   │   │   ├── mentor_home.css
│   │   │   ├── not_enough_points.css
│   │   │   ├── reward.css
│   │   │   ├── shop_home.css
│   │   │   ├── shop_no_rewards.css
│   │   │   ├── shop_redeem_points.css
│   │   │   └── shop_redemption_success.css
│   │   │
│   │   ├── images/
│   │   │   ├── volunteen_logo.jpeg
│   │   │   ├── volunteen.jpg
│   │   │   └── logo.png
│   │   │
│   │   └── js/
│   │       ├── child_home.js
│   │       ├── list_tasks.js
│   │       ├── mentor_children_details.js
│   │       ├── mentor_completed_task_view.js
│   │       ├── mentor_home.js
│   │       ├── mentor_task.js
│   │       ├── reward.js
│   │       ├── scripts.js
│   │       ├── shop_home.js
│   │       └── shop_redemption_history.js
│   │
│   ├── teenApp/
│   │   ├── __pycache__/
│   │   ├── entities/
│   │   │   ├── __pycache__/
│   │   │   ├── __init__.py
│   │   │   ├── child.py
│   │   │   ├── mentor.py
│   │   │   ├── redemption.py
│   │   │   ├── reward.py
│   │   │   ├── shop.py
│   │   │   └── task.py
│   │   │
│   │   ├── interface_adapters/
│   │   │   ├── __pycache__/
│   │   │   ├── __init__.py
│   │   │   ├── forms.py
│   │   │   ├── repositories.py
│   │   │   ├── urls.py
│   │   │   └── views.py
│   │   │
│   │   ├── templates/
│   │   │   ├── two_factor/
│   │   │   ├── add_task.html
│   │   │   ├── assign_bonus.html
│   │   │   ├── assign_points.html
│   │   │   ├── assign_task.html
│   │   │   ├── base.html
│   │   │   ├── child_active_list.html
│   │   │   ├── child_completed_tasks.html
│   │   │   ├── child_home.html
│   │   │   ├── child_points_history.html
│   │   │   ├── confirm_reward.html
│   │   │   ├── edit_task.html
│   │   │   ├── list_tasks.html
│   │   │   ├── mentor_children_details.html
│   │   │   ├── mentor_completed_tasks_view.html
│   │   │   ├── mentor_home.html
│   │   │   ├── not_enough_points.html
│   │   │   ├── points_assigned_success.html
│   │   │   ├── points_leaderboard.html
│   │   │   ├── shop_base.html
│   │   │   ├── shop_invalid_identifier.html
│   │   │   ├── shop_no_rewards.html
│   │   │   ├── shop_not_enough_points.html
│   │   │   ├── shop_redemption_history.html
│   │   │   └── shop_redemption_success.html
│   │   │
│   │   ├── use_cases/
│   │   │   ├── __pycache__/
│   │   │   ├── __init__.py
│   │   │   ├── assign_bonus_points.py
│   │   │   ├── assign_points.py
│   │   │   ├── assign_task.py
│   │   │   └── manage_child.py
│   │   │
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── tests.py
│   │   └── views.py
│   │
│   └── db.sqlite3
│
├── media/
│
└── manage.py


## Usage
To use Volunteen, follow these steps:

1. Run the Django development server:
   ```bash
   python manage.py runserver
2. Open your web browser and navigate to http://127.0.0.1:8000/ to access the homepage.
3. Log in using the appropriate user credentials:
 - For children: use the credentials provided during registration.
 - For mentors: use the mentor credentials.
 - For shop owners: use the shop owner credentials.
4. Children can view and complete tasks assigned to them, earning points for each completed task.
5. Mentors can assign tasks to children and monitor their progress.
6. Shop owners can manage reward redemptions and track points used by children.
7. Use the admin panel to manage users, tasks, and rewards: http://127.0.0.1:8000/admin/ .. username: Adam, Password: 12131415a


## Built With
- [Python](https://www.python.org/) - The programming language used.
- [Django](https://www.djangoproject.com/) - The web framework used.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

