import os

from app.database import init_db


os.environ["OPENAI_API_KEY"] = ""
os.environ["OPENAI_MODEL"] = "gpt-5.2"


def pytest_sessionstart(session):
    init_db()
