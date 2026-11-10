import os

import mysql.connector
from mysql.connector import Error


def get_db_config():
    """Return the database configuration using environment variables with safe defaults."""
    return {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "cortamato"),
        "charset": "utf8mb4",
        "autocommit": True,
        "raise_on_warnings": True,
    }


def get_connection():
    """Create and return a MySQL connection."""
    try:
        connection = mysql.connector.connect(**get_db_config())
        if connection.is_connected():
            return connection
        raise ConnectionError("Could not establish a database connection.")
    except Error as exc:
        raise ConnectionError(f"Unable to connect to MySQL: {exc}") from exc


def close_connection(connection):
    """Close the database connection if it is open."""
    if connection is not None and connection.is_connected():
        connection.close()


if __name__ == "__main__":
    try:
        conn = get_connection()
        print("Connection successful")
        close_connection(conn)
    except ConnectionError as exc:
        print(exc)
