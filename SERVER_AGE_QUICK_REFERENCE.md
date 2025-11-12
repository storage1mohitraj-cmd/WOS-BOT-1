# 🚀 Quick Reference - Server Age Commands

## Commands Overview

| Command | Parameters | Purpose |
|---------|-----------|---------|
| `/server_age` | `days: <number>` | Check server age and next milestone |
| `/timeline` | None | View complete game timeline |

---

## `/server_age` - Quick Examples

**Day 50 Server:**
```
/server_age days:50
→ Shows: Day 50, next is Sunfire Castle (Day 53)
```

**Day 120 Server:**
```
/server_age days:120
→ Shows: Day 120, next is Third Pets Update (Day 140)
```

**Day 500+ Server:**
```
/server_age days:500
→ Shows: Day 500, next is Gen 8 Heroes (Day 520)
```

---

## Timeline Milestones (Quick Reference)

| Day Range | What Unlocks |
|-----------|-------------|
| **0-39** | Initial heroes, Tundra, Fertile Land |
| **40-54** | Gen 2 Heroes, Sunfire Castle, First Pets |
| **60-90** | Fire Crystal Age, SVS/KOI, Second Pets |
| **120-150** | Gen 3 Heroes, Crystal Infrastructure |
| **180-220** | Legendary Equipment, Gen 4, War Academy |
| **270-315** | Gen 5 Heroes, Advanced Crystals |
| **360-440** | Gen 6-7 Heroes, Mammoth |
| **500-600** | Crystal Mastery, Gen 8-9 Heroes |
| **700-951** | Gen 10-13 Heroes |

---

## How to Find Your Server Age

**Method 1:** In-game
1. Open game settings
2. Look for "Server Info" or "State Number"
3. Note the day count

**Method 2:** Online Tool
1. Visit https://whiteoutsurvival.pl/state-timeline/
2. Enter your state number
3. Copy the day count shown

**Method 3:** Bot Command
1. Use `/server_age days:<your_day_count>`

---

## What Each Command Shows

### `/server_age`
✅ Current server age (days + weeks)
✅ Next milestone name & description
✅ Days until next milestone
✅ Recent 3 milestones reached
✅ Links to resources

### `/timeline`
✅ Overview of all milestones
✅ Complete timeline (30+ events)
✅ Split into readable embeds
✅ Source attribution

---

## Common Questions

**Q: How do I find my server day?**
A: Check in-game (Settings > Server Info) or use https://whiteoutsurvival.pl/state-timeline/

**Q: What if my server is past day 951?**
A: The next milestones aren't known yet. Check back later as the game progresses!

**Q: Can I use this in DMs?**
A: Yes, the commands work anywhere the bot can access.

**Q: How often is the timeline updated?**
A: Update it whenever new milestones are released. See IMPLEMENTATION_SUMMARY.md for how.

---

## Emojis Used

| Emoji | Meaning |
|-------|---------|
| 🌍 | Server Information |
| ⏱️ | Time/Age |
| 🎯 | Next Milestone |
| 📜 | Recent Events |
| 📚 | Resources |
| 🏆 | Achievement/End of timeline |
| ⏰ | Countdown |

---

## Troubleshooting Quick Tips

| Issue | Solution |
|-------|----------|
| Commands not appearing | Wait 5-10 seconds, refresh Discord, restart bot |
| "Invalid days" error | Use a positive number: `/server_age days:120` |
| Wrong data shown | Verify your server day count in-game first |
| Bot offline | Check console for errors, restart |

---

**Need help?** Check the full documentation:
- `SERVER_AGE_COMMAND.md` - Complete setup guide
- `SERVER_AGE_EXAMPLES.md` - Detailed examples
- `IMPLEMENTATION_SUMMARY.md` - Technical details

**Ready to use?** Just restart your bot! 🎉
