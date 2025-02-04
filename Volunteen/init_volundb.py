

# python manage.py runserver
# python3 -m venv env_name
# pip install -r requirements.txt
# get data from json and put in db - python manage.py loaddata adjusted_backup.json --verbosity 3
# volunteen_env -> scripts -> activate
    # python manage.py runserver
    # python manage.py makemigrations
    # python manage.py migrate



import psycopg2
from psycopg2 import sql

# Database connection details for the existing Postgres instance
HOST = "localhost"  # Replace with your Docker container's host if different
PORT = 5432         # Default PostgreSQL port
ADMIN_USER = "postgres"  # Adjust if your admin user is different
ADMIN_PASSWORD = "admin"  # Replace with your actual password

# New database details
DATABASE_NAME = "voludb"
DATABASE_USER = "voludbuser"
DATABASE_PASSWORD = "X!e2TbF5qD@t@2&zV01unteen"

try:
    # Connect to the PostgreSQL server as the admin user
    with psycopg2.connect(
        host=HOST, port=PORT, user=ADMIN_USER, password=ADMIN_PASSWORD
    ) as conn:
        # Enable autocommit for database creation
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # Create the new database
            print(f"Creating database '{DATABASE_NAME}'...")
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE_NAME))
            )
            print(f"Database '{DATABASE_NAME}' created successfully.")
        conn.autocommit = False  # Revert autocommit setting if necessary

    # Connect to the new database to create the user and grant privileges
    with psycopg2.connect(
        host=HOST, port=PORT, dbname=DATABASE_NAME, user=ADMIN_USER, password=ADMIN_PASSWORD
    ) as conn:
        with conn.cursor() as cursor:
            # Create the new user
            print(f"Creating user '{DATABASE_USER}'...")
            cursor.execute(
                sql.SQL("CREATE USER {} WITH PASSWORD %s").format(sql.Identifier(DATABASE_USER)),
                [DATABASE_PASSWORD],
            )
            print(f"User '{DATABASE_USER}' created successfully.")

            # Grant privileges to the new user
            print(f"Granting privileges to user '{DATABASE_USER}' on database '{DATABASE_NAME}'...")
            cursor.execute(
                sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {} TO {}").format(
                    sql.Identifier(DATABASE_NAME), sql.Identifier(DATABASE_USER)
                )
            )
            print(f"Privileges granted successfully.")

except psycopg2.Error as e:
    print(f"Error: {e}")
