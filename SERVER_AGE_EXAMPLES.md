# Server Age Command - Usage Examples

## `/server_age` Command Examples

The command automatically fetches your server age from the website by server number.

### Example 1: Checking State 1234
```
Command: /server_age server_number:1234
Bot is fetching... ⏳

Response:
🌍 Server Age Information
State 1234 is on Day 50

⏱️ Server Age
**50** days (~7 weeks)

🎯 Next Milestone
**Day 53**: Sunfire Castle
Coming in **3** days
_Sunfire Castle becomes the battleground for state alliances_

📜 Recent Milestones
• **Day 39**: Fertile Land
• **Day 40**: Gen 2 Heroes
• **Day 54**: First Pets Update

📚 Resources
[Check Your Server](https://whiteoutsurvival.pl/state-timeline/)
[Full State Timeline](https://whiteoutsurvival.pl/state-timeline/)
[Whiteout Survival Official](https://whiteoutsurvival.pl/)

Data scraped from whiteoutsurvival.pl | Updates every 24 hours
```

### Example 2: Checking State 5678
```
Command: /server_age server_number:5678
Bot is fetching... ⏳

Response:
🌍 Server Age Information
State 5678 is on Day 120

⏱️ Server Age
**120** days (~17 weeks)

🎯 Next Milestone
**Day 140**: Third Pets Update
Coming in **20** days
_Giant Elk, Snow Leopard unlocked_

📜 Recent Milestones
• **Day 90**: Second Pets Update
• **Day 120**: Gen 3 Heroes
• **Day 140**: Third Pets Update

📚 Resources
[Check Your Server](https://whiteoutsurvival.pl/state-timeline/)
[Full State Timeline](https://whiteoutsurvival.pl/state-timeline/)
[Whiteout Survival Official](https://whiteoutsurvival.pl/)

Data scraped from whiteoutsurvival.pl | Updates every 24 hours
```

### Example 3: Checking State 9999 (High Day Count)
```
Command: /server_age server_number:9999
Bot is fetching... ⏳

Response:
🌍 Server Age Information
State 9999 is on Day 500

⏱️ Server Age
**500** days (~71 weeks)

🎯 Next Milestone
**Day 520**: Gen 8 Heroes
Coming in **20** days
_Gatot, Hendrik, Sonya released_

📜 Recent Milestones
• **Day 440**: Gen 7 Heroes
• **Day 500**: Crystal Mastery
• **Day 520**: Gen 8 Heroes

📚 Resources
[Check Your Server](https://whiteoutsurvival.pl/state-timeline/)
[Full State Timeline](https://whiteoutsurvival.pl/state-timeline/)
[Whiteout Survival Official](https://whiteoutsurvival.pl/)

Data scraped from whiteoutsurvival.pl | Updates every 24 hours
```

### Example 4: Invalid Server Number
```
Command: /server_age server_number:invalidtext
Response: ❌ Invalid server number! Please enter only digits (e.g., /server_age server_number:1234)
```

### Example 5: Server Number Not Found
```
Command: /server_age server_number:99999999
Response: ❌ Could not find server age. Server number might be invalid or website structure changed.

💡 Tip: Visit https://whiteoutsurvival.pl/state-timeline/ and enter your state number to verify it's correct.
```

---

## `/timeline` Command Example

```
Command: /timeline
Response: (Multiple Embeds)

Embed 1:
🌍 Complete Whiteout Survival Timeline
Here's what unlocks as your server ages

📊 Total Milestones: 30 major events tracked
🎮 Latest Gen: Gen 13 Heroes at Day 951

Embed 2:
Timeline - Part 1
- Day 0: Initial Heroes
- Day 14: Tundra
- Day 34: Arena opponent Update
- Day 39: Fertile Land
- Day 40: Gen 2 Heroes
- Day 53: Sunfire Castle

Embed 3:
Timeline - Part 2
- Day 54: First Pets Update
- Day 60: Fire Crystal Age
- Day 80: SVS and KOI
- Day 90: Second Pets Update
- Day 120: Gen 3 Heroes
- Day 140: Third Pets Update

(... and so on for all milestones ...)

Final Embed:
📖 Source
Timeline data extracted from [Whiteout Survival State Timeline](https://whiteoutsurvival.pl/state-timeline/)
```

---

## How to Find Your Server Number

Your server number is also called your "State Number" in the game.

**Method 1:** In-Game
1. Open Whiteout Survival
2. Check Settings or Profile
3. Look for "State Number" (usually 4 digits)
4. Example: State 1234

**Method 2:** Online Check
1. Visit https://whiteoutsurvival.pl/state-timeline/
2. Look at the form field
3. You can see examples of state numbers there

**Method 3:** Alliance Info
- Your server number is typically in alliance chat or descriptions
- Usually formatted as "State XXXX" or "S#XXXX"

---

## Common Issues & Solutions

| Issue | Solution |
|-------|----------|
| "Invalid server number" | Make sure to enter only numbers, no letters or special characters |
| "Could not find server age" | Verify the state number is correct on the official website |
| Bot says "Request timed out" | Try again in a few seconds, website might be busy |
| Wrong day count shown | Website data might not be updated yet, try again in 24 hours |

---

## Timeline Data Quick Reference

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

## Tips

- The bot fetches real-time data from whiteoutsurvival.pl
- Server ages update daily on the website
- Multiple states might have similar ages
- If your state just launched, it might show as Day 0 or 1
- Bookmark the command for quick access: `/server_age`

**Ready to check?** Just type `/server_age server_number:<your_state_number>` 🚀

