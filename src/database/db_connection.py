import mysql.connector
from mysql.connector import Error
import os

class DatabaseConnection:
    def __init__(self):
        self.host = 'mysql'  # Docker服务名
        self.database = 'stock_analysis'
        self.user = 'stock_user'
        self.password = 'stock_password'
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                database=self.database,
                user=self.user,
                password=self.password
            )
            if self.connection.is_connected():
                print("成功连接到MySQL数据库")
                return True
        except Error as e:
            print(f"连接数据库时出错: {e}")
            return False

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL连接已关闭")

    def execute_query(self, query, params=None):
        if not self.connection or not self.connection.is_connected():
            self.connect()
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            print(f"执行查询时出错: {e}")
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
            print(f"执行更新时出错: {e}")
            self.connection.rollback()
            return 0
        finally:
            cursor.close()