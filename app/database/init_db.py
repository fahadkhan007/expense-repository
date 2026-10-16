from pymongo.errors import PyMongoError

from app.database.connectdb import db


async def init_db():
    try:
        existing_collections = await db.list_collection_names()

        collections = [
            "users",
            "transactions",
            "categories",
            "budgets"
        ]

        for collection in collections:
            if collection not in existing_collections:
                await db.create_collection(collection)
                print(f"Collection '{collection}' created successfully.")
            else:
                print(f"Collection '{collection}' already exists.")

        await db.users.create_index("email", unique=True)

        await db.categories.create_index(
            [("user_id", 1), ("name", 1)],
            unique=True
        )

        await db.budgets.create_index(
            [("user_id", 1), ("month", 1)],
            unique=True
        )

        await db.transactions.create_index(
            [("user_id", 1), ("dateTime", -1)]
        )

        print("Database initialized successfully.")

    except PyMongoError as e:
        print(f"An error occurred while initializing the database: {e}")
        raise