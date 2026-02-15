import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()

def db_connection ():
    # try:
    #     # Establish a connection to the PostgreSQL database
    #     connection = psycopg2.connect(
    #         dbname=os.getenv("DB_NAME"),
    #         user=os.getenv("DB_USER"),
    #         password=os.getenv("DB_PASSWORD"),
    #         host=os.getenv("DB_HOST"),
    #         port=os.getenv("DB_PORT")
    #     )
    #     print("Database connection established successfully.")
    #     connection.close()  # Close the connection after use
    # except Exception as e:
    #     print(f"Error connecting to the database: {e}")
    
    return psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT"),
            cursor_factory=RealDictCursor
        )
    


