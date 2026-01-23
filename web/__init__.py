from flask import Flask
from datetime import timedelta
import os

app = Flask(__name__)

app.config.update(
    {
        "PERMANENT_SESSION_LIFETIME": timedelta(hours=12),
        "SECRET_KEY": os.urandom(16).hex()
    }
)

from web import views