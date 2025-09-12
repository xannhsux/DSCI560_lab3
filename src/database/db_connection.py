import mysql.connector
from mysql.connector import Error
import time

class DatabaseConnection:
    def __init__(self):
        self.host = 'mysql'  # Docker service name
        self.database = 'stock_analysis'
        self.user = 'stock_user'
        self.password = 'stock_password'
        self.connection = None

    def connect(self, max_retries=5):
        """Connect to MySQL database with retry logic"""
        for attempt in range(max_retries):
            try:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    database=self.database,
                    user=self.user,
                    password=self.password
                )
                if self.connection.is_connected():
                    print("Successfully connected to MySQL database")
                    return True
            except Error as e:
                print(f"Attempt {attempt + 1}: Error connecting to database: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in 5 seconds...")
                    time.sleep(5)
                else:
                    print("Failed to connect after all attempts")
                    return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")

    def execute_query(self, query, params=None):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            print(f"Error executing query: {e}")
            return None
        finally:
            cursor.close()

    def execute_update(self, query, params=None):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount
        except Error as e:
            print(f"Error executing update: {e}")
            self.connection.rollback()
            return 0
        finally:
            cursor.close()