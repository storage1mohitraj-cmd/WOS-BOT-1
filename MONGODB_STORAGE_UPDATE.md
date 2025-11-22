# MongoDB Storage Update Guide

## Issue
The MongoDB storage class (`db/reminder_storage_mongo.py`) needs to be updated to support the new `body` parameter.

## Required Changes

### 1. Update the `add_reminder` method signature

**Find this line (approximately):**
```python
def add_reminder(self, user_id: str, channel_id: str, guild_id: str, message: str, reminder_time: datetime,
                is_recurring: bool = False, recurrence_type: str = None, recurrence_interval: int = None,
                original_pattern: str = None, mention: str = 'everyone', image_url: str = None,
                thumbnail_url: str = None, author_name: str = None, author_icon_url: str = None,
                footer_text: str = None, footer_icon_url: str = None) -> int:
```

**Change it to:**
```python
def add_reminder(self, user_id: str, channel_id: str, guild_id: str, message: str, reminder_time: datetime,
                body: str = None, is_recurring: bool = False, recurrence_type: str = None, recurrence_interval: int = None,
                original_pattern: str = None, mention: str = 'everyone', image_url: str = None,
                thumbnail_url: str = None, footer_text: str = None, footer_icon_url: str = None) -> int:
```

**Changes:**
- Added `body: str = None` parameter after `reminder_time`
- Removed `author_name: str = None`
- Removed `author_icon_url: str = None`

### 2. Update the MongoDB document insertion

**Find the document creation (approximately):**
```python
reminder_doc = {
    'user_id': user_id,
    'channel_id': channel_id,
    'guild_id': guild_id,
    'message': message,
    'reminder_time': reminder_time,
    'created_at': datetime.utcnow(),
    'is_active': True,
    'is_sent': False,
    'is_recurring': is_recurring,
    'recurrence_type': recurrence_type,
    'recurrence_interval': recurrence_interval,
    'original_time_pattern': original_pattern,
    'mention': mention,
    'image_url': image_url,
    'thumbnail_url': thumbnail_url,
    'author_name': author_name,
    'author_icon_url': author_icon_url,
    'footer_text': footer_text,
    'footer_icon_url': footer_icon_url
}
```

**Change it to:**
```python
reminder_doc = {
    'user_id': user_id,
    'channel_id': channel_id,
    'guild_id': guild_id,
    'message': message,
    'body': body,
    'reminder_time': reminder_time,
    'created_at': datetime.utcnow(),
    'is_active': True,
    'is_sent': False,
    'is_recurring': is_recurring,
    'recurrence_type': recurrence_type,
    'recurrence_interval': recurrence_interval,
    'original_time_pattern': original_pattern,
    'mention': mention,
    'image_url': image_url,
    'thumbnail_url': thumbnail_url,
    'footer_text': footer_text,
    'footer_icon_url': footer_icon_url
}
```

**Changes:**
- Added `'body': body,` after `'message': message,`
- Removed `'author_name': author_name,`
- Removed `'author_icon_url': author_icon_url,`

## Steps to Apply

1. Open `f:\STARK-whiteout survival bot\DISCORD BOT\db\reminder_storage_mongo.py`
2. Make the changes described above
3. Save the file
4. Restart the bot

## After Restart

The bot should now:
- Accept the `body` parameter in reminders
- Store it in MongoDB
- Display message as title and body as description
- No longer use author fields
