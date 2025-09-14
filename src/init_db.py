import sys
sys.path.append('.')
from database.db_connection import create_connection, initialize_database

try:
    conn = create_connection()
    if conn:
        print('Database connection successful')
        initialize_database(conn)
        print('Database tables initialized')
        conn.close()
        print('Database initialization complete')
    else:
        print('Failed to connect to database')
except Exception as e:
    print(f'Error: {e}')
