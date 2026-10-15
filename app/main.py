from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database.connectdb import close_db, connect_db
from app.database.init_db import init_db


@asynccontextmanager # type: ignore
async def lifespan(app: FastAPI):
    try:
        await connect_db()
        await init_db()
        yield
    except Exception as e:  # noqa: BLE001
        print(f"An error occurred during the application lifespan: {e}")
    finally:
        await close_db()


app=FastAPI(
        title="expense tracker app", 
        description="This is an expense tracker app built with FastAPI", 
        version="1.0.0",
        lifespan=lifespan
    )


@app.get("/")
def home():
    return {
        "message": "welcome to the expense tracker app"
    }