# 🎮 Server Age Command - Visual Guide

## Command Usage

```
┌─────────────────────────────────────────────────────┐
│ Type in Discord:                                    │
│ /server_age server_number:1234                      │
│                    ↓                                 │
│                  Bot loads                          │
│                    ↓                                 │
│           Scrapes website for State 1234            │
│                    ↓                                 │
│          Extracts age and milestones                │
│                    ↓                                 │
│        Displays beautiful embed response            │
└─────────────────────────────────────────────────────┘
```

---

## Response Layout

```
╔════════════════════════════════════════════════════╗
║                                                    ║
║  🌍 Server Age Information                         ║
║  State 1234 is on Day 50                           ║
║                                                    ║
║  ⏱️ Server Age                                      ║
║  50 days (~7 weeks)                                ║
║                                                    ║
║  🎯 Next Milestone                                  ║
║  Day 53: Sunfire Castle                            ║
║  Coming in 3 days                                  ║
║  Sunfire Castle becomes the battleground...        ║
║                                                    ║
║  📜 Recent Milestones                               ║
║  • Day 39: Fertile Land                            ║
║  • Day 40: Gen 2 Heroes                            ║
║  • Day 54: First Pets Update                       ║
║                                                    ║
║  📚 Resources                                       ║
║  [Links to check and learn more]                   ║
║                                                    ║
╚════════════════════════════════════════════════════╝
```

---

## How It Works (Simplified)

```
User Input
    ↓
[/server_age server_number:1234]
    ↓
Bot validates (digits only)
    ↓
Bot makes HTTP request to website
    ↓
Website returns HTML page
    ↓
Bot parses with BeautifulSoup
    ↓
Bot searches with regex patterns
    ↓
Bot extracts: Day 50
    ↓
Bot matches to milestones
    ↓
Bot creates embed
    ↓
User sees result!
```

---

## Command Reference

### Main Command
```
/server_age server_number:<number>

Examples:
- /server_age server_number:1234
- /server_age server_number:5000
- /server_age server_number:999
```

### Alternative Commands
```
/timeline
→ Shows complete game timeline (no parameters needed)
```

---

## Key Information

### What You Need
- Your **State Number** (4 digits, in-game)
- Nothing else! Bot does the rest

### What You Get
- Server age in days
- Server age in weeks
- Next milestone name
- Days until next milestone
- Recent milestones reached
- Links to resources

### Timeline Covered
- **Day 0**: Initial Heroes
- **Day 14**: Tundra
- **...** (30 milestones total)
- **Day 951**: Gen 13 Heroes

---

## Error Messages & Solutions

```
Error: "Invalid server number"
Solution: Only use digits (1234 not S1234)

Error: "Could not find server age"
Solution: Verify server number is correct
         Check: https://whiteoutsurvival.pl/state-timeline/

Error: "Request timed out"
Solution: Website busy, try again in a few seconds

Success: Beautiful embed with all info!
```

---

## Emoji Guide

| Emoji | Meaning |
|-------|---------|
| 🌍 | Server/World info |
| ⏱️ | Time/Age |
| 🎯 | Target/Next event |
| 📜 | History/Past events |
| 📚 | Resources/Links |
| 🏆 | Achievement |

---

## Quick Access Card

```
╔═══════════════════════════════════════╗
║  WHITEOUT SURVIVAL SERVER AGE BOT    ║
║                                       ║
║  Command: /server_age                ║
║  Parameter: server_number            ║
║                                       ║
║  Example: /server_age server_number:1234
║                                       ║
║  Need help? Type: /timeline           ║
║  or visit: whiteoutsurvival.pl        ║
╚═══════════════════════════════════════╝
```

---

## Timeline Preview

```
Day 0-50:    Initial Heroes → Fertile Land → First Pets
Day 50-150:  Sunfire Castle → Gen 3 Heroes → Infrastructure
Day 150-300: Equipment → War Academy → Gen 5 Heroes
Day 300+:    Advanced Crystals → Gen 6-13 Heroes
```

---

## Features at a Glance

```
✅ Automatic web scraping
✅ Real server data
✅ Beautiful formatting
✅ Next milestone countdown
✅ Error handling
✅ Fast response
✅ No setup needed
✅ Works anywhere
```

---

## Getting Started in 3 Steps

```
Step 1: Find your server number (in-game)
        Example: 1234

Step 2: Type the command
        /server_age server_number:1234

Step 3: View your results!
        Beautiful embed with all info
```

---

## Support

**Questions?** Check these files:
- `SERVER_AGE_QUICK_START.md` - Simple guide
- `SERVER_AGE_EXAMPLES.md` - Real examples
- `SERVER_AGE_COMMAND.md` - Full documentation

**Still stuck?** Restart the bot or check Discord logs.

---

**Ready?** 🚀 Type it now!

```
/server_age server_number:
```

Then enter your state number!
