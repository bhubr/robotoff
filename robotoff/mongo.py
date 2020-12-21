from pymongo import MongoClient

from robotoff import settings
from robotoff.utils.cache import CachedStore


def get_mongo_client() -> MongoClient:
    return MongoClient(settings.MONGO_URI)


MONGO_CLIENT_CACHE = CachedStore(get_mongo_client, expiration_interval=None)
