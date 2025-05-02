import os
from dotenv import load_dotenv

load_dotenv()

# Database connection settings
SQL_SERVER_MOFLES = os.getenv('SQL_SERVER_MOFLES', r'TALLERSVR\SQLEXPRESS')
SQL_SERVER_GARCIA = os.getenv('SQL_SERVER_GARCIA', r'192.168.1.70\SQLEXPRESS')
DATABASE = os.getenv('DATABASE', 'TuBaseDeDatos')
USERNAME = os.getenv('DB_USERNAME', 'TuUsuario')
PASSWORD = os.getenv('DB_PASSWORD', 'TuContraseña')