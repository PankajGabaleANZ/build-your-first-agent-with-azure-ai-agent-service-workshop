import os

from chainlit.utils import mount_chainlit
from fastapi import FastAPI

# Map environment to target path
env = os.getenv("ENV", "development")
target = {"development": "src/workshop/main.py", "production": "src/workshop/main.py"}.get(env)

app = FastAPI()
mount_chainlit(app=app, target=target, path="/sales")