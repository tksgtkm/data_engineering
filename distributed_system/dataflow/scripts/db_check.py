import os
import mysql.connector
import psycopg2

def check_mysql():
    conn = mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        database=os.getenv("MYSQL_DB", "dataflow"),
        user=os.getenv("MYSQL_USER", "dataflow_user"),
        password=os.getenv("MYSQL_PASSWORD", "dataflow_pass"),
    )
    cursor = conn.cursor()
    cursor.execute("SELECT VERSION()")
    version = cursor.fetchone()
    print(f"MySQL connected: {version[0]}")
    cursor.close()
    conn.close()

def check_postgres():
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "dataflow"),
        user=os.getenv("POSTGRES_USER", "dataflow_user"),
        password=os.getenv("POSTGRES_PASSWORD", "dataflow_pass"),
    )
    cursor = conn.cursor()
    cursor.execute("SELECT version()")
    version = cursor.fetchone()
    print(f"PostgreSQL connected: {version[0]}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_mysql()
    check_postgres()
