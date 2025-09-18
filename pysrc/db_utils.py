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

    def fetch_test_data_by_uniq_id(self, uniq_id, table='vperf'):
        """
        Fetches test data from the database using the Uniq ID.
        """

        job_data = self.fetch_query("select date,build,test_name,bw,iops,latency,cluster,uniq from %s where uniq=%s;" % (table, uniq_id))
        if job_data:
            return job_data
        else:
            print(f"No data found for Uniq ID: {uniq_id}")
            return None