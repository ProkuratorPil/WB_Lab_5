"""
Database connection module for MongoDB.
Uses Motor (async driver) and Beanie (ODM) for document management.
"""
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Motor client
client: AsyncIOMotorClient = None


async def init_db():
    """
    Initialize MongoDB connection and Beanie ODM.
    Called during application startup.
    """
    global client
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGO_URI[:settings.MONGO_URI.find('@') + 1]}...")
        client = AsyncIOMotorClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
        )
        # Ping to verify connection
        await client.admin.command('ping')
        logger.info("MongoDB connection established successfully")

        # Import all document models
        from app.models.user import UserDocument
        from app.models.token import TokenDocument
        from app.models.uploaded_file import UploadedFileDocument

        # Initialize Beanie with all document models
        # Indexes are created automatically by Beanie when document_models is provided
        await init_beanie(
            database=client[settings.DB_NAME],
            document_models=[
                UserDocument,
                TokenDocument,
                UploadedFileDocument,
            ]
        )
        logger.info("Beanie ODM initialized successfully (indexes auto-created)")

    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise


async def close_db():
    """
    Close MongoDB connection.
    Called during application shutdown.
    """
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed")