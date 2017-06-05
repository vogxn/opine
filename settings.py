import os
from decouple import config

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_URL = "https://api.github.com"
DEBUG = config('DEBUG', cast=bool, default=False)
CLIENT_ID = config('CLIENT_ID')
CLIENT_SECRET = config('CLIENT_SECRET')
SECRET_KEY = config('SECRET_KEY')
