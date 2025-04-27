import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('./.env_vars')

HOST = os.getenv('host')
PORT = os.getenv('port')
DATABASE = os.getenv('database')
USERNAME = 'postgres'  
PASSWORD = os.getenv('password')