# TODO: Redesign Reminder Message Format

## Task: Move message content outside the embed
- Current: Message content is inside the embed description with ANSI coloring
- New: Message content should be plain text below the embed
- Keep: @everyone mention, embed title "⏰ **REMINDER**", mini logo thumbnail

## Steps:
1. ✅ Modify the `check_reminders` method in `reminder_system.py`
2. ✅ Remove the description from the embed (which contains the colored message)
3. ✅ Add the message content to the `content` parameter of `channel.send()`
4. Test the new format

## Files to Edit:
- `reminder_system.py` (around line 700-720 in check_reminders method)
