import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from .mongo_client_wrapper import get_mongo_client

logger = logging.getLogger(__name__)


def _get_db():
    uri = os.getenv('MONGO_URI')
    if not uri:
        raise ValueError('MONGO_URI not set')
    client = get_mongo_client(uri)
    db_name = os.getenv('MONGO_DB_NAME', 'discord_bot')
    return client[db_name]


def mongo_enabled() -> bool:
    return bool(os.getenv('MONGO_URI'))


class UserTimezonesAdapter:
    COLL = 'user_timezones'

    @staticmethod
    def load_all() -> Dict[str, str]:
        try:
            db = _get_db()
            docs = db[UserTimezonesAdapter.COLL].find({})
            return {str(d['_id']): d.get('timezone') for d in docs}
        except Exception as e:
            logger.error(f'Failed to load user_timezones from Mongo: {e}')
            return {}

    @staticmethod
    def get(user_id: str) -> Optional[str]:
        try:
            db = _get_db()
            d = db[UserTimezonesAdapter.COLL].find_one({'_id': str(user_id)})
            return d.get('timezone') if d else None
        except Exception as e:
            logger.error(f'Failed to get timezone for {user_id}: {e}')
            return None

    @staticmethod
    def set(user_id: str, tz_abbr: str) -> bool:
        try:
            db = _get_db()
            now = datetime.utcnow().isoformat()
            db[UserTimezonesAdapter.COLL].update_one(
                {'_id': str(user_id)},
                {'$set': {'timezone': tz_abbr.lower(), 'updated_at': now}, '$setOnInsert': {'created_at': now}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f'Failed to set timezone for {user_id}: {e}')
            return False


class BirthdaysAdapter:
    COLL = 'birthdays'

    @staticmethod
    def load_all() -> Dict[str, Any]:
        try:
            db = _get_db()
            docs = db[BirthdaysAdapter.COLL].find({})
            return {str(d['_id']): {'day': int(d.get('day')), 'month': int(d.get('month'))} for d in docs}
        except Exception as e:
            logger.error(f'Failed to load birthdays from Mongo: {e}')
            return {}

    @staticmethod
    def get(user_id: str):
        try:
            db = _get_db()
            d = db[BirthdaysAdapter.COLL].find_one({'_id': str(user_id)})
            if not d:
                return None
            return {'day': int(d['day']), 'month': int(d['month'])}
        except Exception as e:
            logger.error(f'Failed to get birthday for {user_id}: {e}')
            return None

    @staticmethod
    def set(user_id: str, day: int, month: int) -> bool:
        try:
            db = _get_db()
            db[BirthdaysAdapter.COLL].update_one(
                {'_id': str(user_id)},
                {'$set': {'day': int(day), 'month': int(month), 'updated_at': datetime.utcnow().isoformat()},
                 '$setOnInsert': {'created_at': datetime.utcnow().isoformat()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f'Failed to set birthday for {user_id}: {e}')
            return False

    @staticmethod
    def remove(user_id: str) -> bool:
        try:
            db = _get_db()
            res = db[BirthdaysAdapter.COLL].delete_one({'_id': str(user_id)})
            return res.deleted_count > 0
        except Exception as e:
            logger.error(f'Failed to remove birthday for {user_id}: {e}')
            return False


class UserProfilesAdapter:
    COLL = 'user_profiles'

    @staticmethod
    def load_all() -> Dict[str, Any]:
        try:
            db = _get_db()
            docs = db[UserProfilesAdapter.COLL].find({})
            result = {}
            for d in docs:
                data = d.copy()
                data.pop('_id', None)
                result[str(d['_id'])] = data
            return result
        except Exception as e:
            logger.error(f'Failed to load user profiles from Mongo: {e}')
            return {}

    @staticmethod
    def get(user_id: str) -> Optional[Dict[str, Any]]:
        try:
            db = _get_db()
            d = db[UserProfilesAdapter.COLL].find_one({'_id': str(user_id)})
            if not d:
                return None
            d.pop('_id', None)
            return d
        except Exception as e:
            logger.error(f'Failed to get profile for {user_id}: {e}')
            return None

    @staticmethod
    def set(user_id: str, data: Dict[str, Any]) -> bool:
        try:
            db = _get_db()
            now = datetime.utcnow().isoformat()
            payload = data.copy()
            # Avoid conflicts where payload already contains 'created_at' which
            # would clash with our $setOnInsert created_at below.
            payload.pop('created_at', None)
            payload['updated_at'] = now
            db[UserProfilesAdapter.COLL].update_one({'_id': str(user_id)}, {'$set': payload, '$setOnInsert': {'created_at': now}}, upsert=True)
            return True
        except Exception as e:
            logger.error(f'Failed to set profile for {user_id}: {e}')
            return False


class GiftcodeStateAdapter:
    COLL = 'giftcode_state'

    @staticmethod
    def get_state() -> Dict[str, Any]:
        try:
            db = _get_db()
            d = db[GiftcodeStateAdapter.COLL].find_one({'_id': 'giftcode_state'})
            if not d:
                return {}
            d.pop('_id', None)
            return d
        except Exception as e:
            logger.error(f'Failed to get giftcode state from Mongo: {e}')
            return {}

    @staticmethod
    def set_state(state: Dict[str, Any]) -> bool:
        try:
            db = _get_db()
            now = datetime.utcnow().isoformat()
            payload = state.copy()
            # Remove created_at from payload to avoid $set vs $setOnInsert conflict
            payload.pop('created_at', None)
            payload['updated_at'] = now
            db[GiftcodeStateAdapter.COLL].update_one({'_id': 'giftcode_state'}, {'$set': payload, '$setOnInsert': {'created_at': now}}, upsert=True)
            return True
        except Exception as e:
            logger.error(f'Failed to set giftcode state in Mongo: {e}')
            return False


# ============================================================================
# ALLIANCE DATA ADAPTERS - For storing all alliance member info
# ============================================================================

class AllianceMembersAdapter:
    """Stores alliance members with all their data (player IDs, levels, etc.)"""
    COLL = 'alliance_members'

    @staticmethod
    def upsert_member(fid: str, data: Dict[str, Any]) -> bool:
        """Insert or update a single alliance member"""
        try:
            db = _get_db()
            now = datetime.utcnow().isoformat()
            
            # Ensure _id is string fid
            data_copy = data.copy()
            data_copy['updated_at'] = now
            
            db[AllianceMembersAdapter.COLL].update_one(
                {'_id': str(fid)},
                {'$set': data_copy, '$setOnInsert': {'created_at': now}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f'Failed to upsert alliance member {fid} in Mongo: {e}')
            return False

    @staticmethod
    def get_member(fid: str) -> Optional[Dict[str, Any]]:
        """Get a single alliance member"""
        try:
            db = _get_db()
            doc = db[AllianceMembersAdapter.COLL].find_one({'_id': str(fid)})
            if doc:
                doc.pop('_id', None)  # Remove MongoDB _id
            return doc
        except Exception as e:
            logger.error(f'Failed to get alliance member {fid} from Mongo: {e}')
            return None

    @staticmethod
    def get_all_members() -> list:
        """Get all alliance members"""
        try:
            db = _get_db()
            docs = list(db[AllianceMembersAdapter.COLL].find({}))
            for doc in docs:
                doc.pop('_id', None)  # Remove MongoDB _id
            return docs
        except Exception as e:
            logger.error(f'Failed to get all alliance members from Mongo: {e}')
            return []

    @staticmethod
    def delete_member(fid: str) -> bool:
        """Delete a single alliance member"""
        try:
            db = _get_db()
            result = db[AllianceMembersAdapter.COLL].delete_one({'_id': str(fid)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f'Failed to delete alliance member {fid} from Mongo: {e}')
            return False

    @staticmethod
    def clear_all() -> bool:
        """Clear all alliance members"""
        try:
            db = _get_db()
            db[AllianceMembersAdapter.COLL].delete_many({})
            logger.info('[Mongo] Cleared all alliance members')
            return True
        except Exception as e:
            logger.error(f'Failed to clear alliance members from Mongo: {e}')
            return False


class AllianceMetadataAdapter:
    """Stores alliance metadata (settings, config, etc.)"""
    COLL = 'alliance_metadata'

    @staticmethod
    def set_metadata(key: str, value: Any) -> bool:
        """Set alliance metadata"""
        try:
            db = _get_db()
            now = datetime.utcnow().isoformat()
            
            db[AllianceMetadataAdapter.COLL].update_one(
                {'_id': str(key)},
                {'$set': {'value': value, 'updated_at': now}, '$setOnInsert': {'created_at': now}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f'Failed to set alliance metadata {key}: {e}')
            return False

    @staticmethod
    def get_metadata(key: str) -> Optional[Any]:
        """Get alliance metadata"""
        try:
            db = _get_db()
            doc = db[AllianceMetadataAdapter.COLL].find_one({'_id': str(key)})
            return doc.get('value') if doc else None
        except Exception as e:
            logger.error(f'Failed to get alliance metadata {key}: {e}')
            return None


class GiftCodesAdapter:
    """Adapter for managing gift codes in MongoDB (for gift_operationsapi cog)"""
    COLL = 'gift_codes'

    @staticmethod
    def get_all():
        """Get all gift codes as list of tuples: (code, date, validation_status)"""
        try:
            db = _get_db()
            docs = db[GiftCodesAdapter.COLL].find({})
            return [(d.get('_id'), d.get('date'), d.get('validation_status')) for d in docs]
        except Exception as e:
            logger.error(f'Failed to get all gift codes from Mongo: {e}')
            return []

    @staticmethod
    def insert(code: str, date: str, validation_status: str = 'pending') -> bool:
        """Insert a new gift code (ignores if already exists)"""
        try:
            db = _get_db()
            db[GiftCodesAdapter.COLL].update_one(
                {'_id': code},
                {'$set': {'date': date, 'validation_status': validation_status, 'created_at': datetime.utcnow().isoformat()}},
                upsert=True
            )
            return True
        except Exception as e:
            logger.error(f'Failed to insert gift code {code}: {e}')
            return False

    @staticmethod
    def update_status(code: str, validation_status: str) -> bool:
        """Update validation status of a gift code"""
        try:
            db = _get_db()
            db[GiftCodesAdapter.COLL].update_one(
                {'_id': code},
                {'$set': {'validation_status': validation_status, 'updated_at': datetime.utcnow().isoformat()}}
            )
            return True
        except Exception as e:
            logger.error(f'Failed to update status for {code}: {e}')
            return False

    @staticmethod
    def delete(code: str) -> bool:
        """Delete a gift code"""
        try:
            db = _get_db()
            result = db[GiftCodesAdapter.COLL].delete_one({'_id': code})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f'Failed to delete gift code {code}: {e}')
            return False

    @staticmethod
    def clear_all() -> bool:
        """Clear all gift codes (use with caution)"""
        try:
            db = _get_db()
            db[GiftCodesAdapter.COLL].delete_many({})
            return True
        except Exception as e:
            logger.error(f'Failed to clear all gift codes: {e}')
            return False


# Explicit exports for reliable module import on all platforms (Render, Docker, local)
__all__ = [
    'mongo_enabled',
    'UserTimezonesAdapter',
    'BirthdaysAdapter',
    'UserProfilesAdapter',
    'GiftcodeStateAdapter',
    'GiftCodesAdapter',
    'AllianceMembersAdapter',
]
