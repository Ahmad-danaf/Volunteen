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
volunteen/
├── README.md
├── requirements.txt
├── src/
│ ├── main.py
│ ├── module1/
│ │ ├── init.py
│ │ ├── file1.py
│ │ └── file2.py
│ ├── module2/
│ │ ├── init.py
│ │ ├── file1.py
│ │ └── file2.py
├── tests/
│ ├── test_module1.py
│ └── test_module2.py
└── docs/
├── design.md
└── usage.md


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

