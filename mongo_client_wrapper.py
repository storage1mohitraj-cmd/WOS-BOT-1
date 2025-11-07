import os
import time
import logging
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import ServerSelectionTimeoutError, PyMongoError

_LOGGER = logging.getLogger(__name__)
_DEFAULT_URI = os.getenv('MONGO_URI')


def get_mongo_client(uri: str | None = None, *, connect_timeout_ms: int | None = None) -> MongoClient:
    """Return a connected MongoClient. Reads MONGO_URI from env if not provided.

    This function will attempt several retries (configurable via MONGO_CONNECT_RETRIES)
    with exponential backoff to tolerate transient network/DNS issues when connecting to
    MongoDB Atlas. The connect timeout may be configured via MONGO_CONNECT_TIMEOUT_MS.

    Raises ValueError if no URI is available or RuntimeError if connection fails after
    the configured retries.
    """
    uri = uri or _DEFAULT_URI
    if not uri:
        raise ValueError('No MongoDB URI provided. Set MONGO_URI in environment or pass uri param')

    # Configurable timeouts/retries via env
    default_timeout = 30000
    if connect_timeout_ms is None:
        try:
            connect_timeout_ms = int(os.getenv('MONGO_CONNECT_TIMEOUT_MS', default_timeout))
        except Exception:
            connect_timeout_ms = default_timeout

    try:
        retries = int(os.getenv('MONGO_CONNECT_RETRIES', '3'))
    except Exception:
        retries = 3

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            _LOGGER.debug('Attempting MongoDB connection (attempt %d/%d) uri=%s timeout=%d', attempt, retries, uri, connect_timeout_ms)
            client = MongoClient(uri, serverSelectionTimeoutMS=connect_timeout_ms, server_api=ServerApi('1'))
            # perform a quick ping to ensure the client can reach a primary
            client.admin.command('ping')
            _LOGGER.info('Connected to MongoDB on attempt %d/%d', attempt, retries)
            return client
        except ServerSelectionTimeoutError as e:
            last_exc = e
            _LOGGER.warning('MongoDB connection attempt %d/%d failed: %s', attempt, retries, e)
            if attempt < retries:
                backoff = 2 ** (attempt - 1)
                _LOGGER.info('Waiting %ds before next MongoDB connection attempt', backoff)
                time.sleep(backoff)
                continue
            else:
                _LOGGER.error('All MongoDB connection attempts failed')
                raise RuntimeError(f'Could not connect to MongoDB after {retries} attempts: {e}') from e
        except PyMongoError as e:
            # Other pymongo errors (auth, TLS, etc.)
            last_exc = e
            _LOGGER.exception('Unexpected PyMongo error while connecting to MongoDB: %s', e)
            raise RuntimeError(f'PyMongo error while connecting to MongoDB: {e}') from e

    # Should not reach here, but raise if we somehow do
    raise RuntimeError(f'Could not connect to MongoDB: {last_exc}')
