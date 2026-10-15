from pymongo import AsyncMongoClient

from app.config.settings import settings

client: AsyncMongoClient = AsyncMongoClient(settings.MONGODB_URI)


db = client[settings.DATABASE_NAME]


async def connect_db():
    await client.admin.command("ping")
    print("database connected successfully!")
    
    
async def close_db():
    await client.close()
    print("database connection closed successfully!")
    
    

    





