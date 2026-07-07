from dotenv import load_dotenv
import os


load_dotenv()


#Database
DATABASE_URI = os.environ['DATABASE_URI']
TEST_DATABASE_URI = os.environ["TEST_DATABASE_URI"]

#Redis
REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "15"))


#SMTP
MAIL_USERNAME = os.environ["MAIL_USERNAME"]
MAIL_PASSWORD = os.environ["MAIL_PASSWORD"]
MAIL_FROM = os.environ["MAIL_FROM"]
MAIL_SERVER = os.environ["MAIL_SERVER"]
MAIL_PORT = int(os.environ["MAIL_PORT"])


#App
APP_NAME = os.getenv('APP_NAME', 'Auth service')


#Security
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ['ACCESS_TOKEN_EXPIRE_MINUTES'])
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ['REFRESH_TOKEN_EXPIRE_DAYS'])