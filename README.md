# Volunteen <img src="Volunteen/Volunteen/static/images/logo.png" alt="Volunteen Logo" width="300"/>

_A social-impact platform that empowers teens to engage in volunteering through gamification, task tracking, and reward-based motivation._

## Overview

Volunteen is built for teens, parents, mentors, and institutions to promote and manage youth volunteering in an engaging and structured way. By using gamified systems like TeenCoins, leaderboards, and streaks, the platform motivates consistent participation while offering tools for supervision, task approval, and rewards.

## Features

- Task Management: Parents, mentors, and institutions can assign tasks to teens.
- Asynchronous Check-In/Out: Teens submit photo proof of task progress.
- TeenCoins System: Earned by task completion and can be donated or redeemed.
- Gamification: Streak tracking, donation leaderboards, and performance analytics.
- Role-Specific Dashboards: Separate experiences for teens, parents, mentors, and institutions.
- Automated Commands: Monthly parent top-ups, cleanup scripts, and more.
- Utility-Driven Architecture: Core logic is modularized for maintainability and scalability.
- Test Coverage: Run modular tests for each app with Django's testing framework.

## Tech Stack

- Frontend: Django Templates (React migration planned)
- Backend: Django
- Database: PostgreSQL
- APIs: Green API (for WhatsApp messaging/automation)
- Deployment: PythonAnywhere / AWS


## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/Volunteen.git
cd Volunteen

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

To enable asynchronous task handling (e.g., photo-based check-in/out), run:

```bash
python manage.py qcluster
```

## Environment Variables

Create a `.env` file in the project root with the following:

```env
GREEN_API=your_key
DEVELOPMENT=True
EMAIL_PASSWORD=your_email_password

DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

X-API-Key=your_internal_api_key
```

## Running Tests

You can run tests per app like this:

```bash
python manage.py test childApp.tests
```

Replace `childApp` with any other app (e.g. `mentorApp`, `teenApp`, etc.)

## Project Structure

```
Volunteen/
├── Volunteen/
│   ├── frameworks_and_drivers/
│   ├── static/
│   ├── media/
│   ├── db.sqlite3
│   ├── constants.py
│   └── manage.py
│
├── childApp/
├── mentorApp/
├── parentApp/
├── institutionApp/
├── managementApp/
├── shopApp/
├── teenApp/
│
├── requirements.txt
├── .env
└── README.md
```

## Contributing

We welcome contributions!  
To contribute:

```bash
# 1. Fork the repository
# 2. Create a new branch
git checkout -b feature/my-feature

# 3. Make your changes and commit
git commit -m "Add new feature"

# 4. Push your branch
git push origin feature/my-feature

# 5. Open a Pull Request
```

## License

This project is licensed under the MIT License.
