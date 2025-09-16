import psycopg2
from psycopg2 import OperationalError
import os

class PostgresDB:
    def __init__(self):
        self.conn = None
        self.host = os.getenv("DB_HOST")
        self.port = os.getenv("DB_PORT", "5432")
        self.dbname = os.getenv("DB_NAME")
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.connect()

    def connect(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.dbname,
                user=self.user,
                password=self.password
            )
            print("Connection successful")
        except OperationalError as e:
            print(f"Connection failed: {e}")

    def execute_query(self, query, params=None):
        if self.conn is None:
            print("Not connected to the database")
            return

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                self.conn.commit()
                print("Query executed successfully")
        except Exception as e:
            print(f"Error executing query: {e}")

    def fetch_query(self, query, params=None):
        if self.conn is None:
            print("Not connected to the database")
            return None

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching query: {e}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()
            print("Connection closed")
