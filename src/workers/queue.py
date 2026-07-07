from saq import Queue
from src.config import REDIS_URL


queue = Queue.from_url(REDIS_URL, name="auth-service")