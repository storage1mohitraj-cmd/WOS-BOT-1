# ⚡ COMMAND READY - API-Based Server Age Finder

## The Command

```
/server_age server_number:1234
```

Replace `1234` with your actual server number!

---

## How It Works

### What Happens Behind the Scenes

1. **Bot sends payload to website API:**
   ```
   POST https://whiteoutsurvival.pl/wp-admin/admin-ajax.php
   
   payload: {
     "action": "check_server_age",
     "state": "1234"
   }
   ```

2. **Website API responds with JSON:**
   ```json
   {
     "success": true,
     "days": 50,
     "open_date": "2025-09-15"
   }
   ```

3. **Bot parses and displays:**
   ```
   🌍 Server Age Information
   State 1234 is on Day 50
   [... milestones, countdown, etc ...]
   ```

---

## Usage in Discord

### Step 1: Type Command
```
/server_age
```

### Step 2: Add Parameter
```
/server_age server_number:
```

### Step 3: Enter Server Number
```
/server_age server_number:1234
```

### Step 4: Get Results!
Beautiful embed appears instantly ✨

---

## Example Results

```
🌍 Server Age Information
State 1234 is on Day 50

⏱️ Server Age
50 days (~7 weeks)

🎯 Next Milestone
Day 53: Sunfire Castle (in 3 days)

📜 Recent Milestones
• Day 39: Fertile Land
• Day 40: Gen 2 Heroes
• Day 54: First Pets Update

📚 Resources
[Links to check yourself]
```

---

## What It Uses

✅ **Website's Official API**
- WordPress AJAX endpoint
- Sends proper payload
- Parses JSON response

✅ **Fallback Strategy**
- If API unavailable, tries direct endpoints
- Falls back to HTML parsing
- Always works!

---

## Bonus Command

```
/timeline
```

Shows complete game timeline (all 30+ milestones)

---

## Error Handling

**Invalid input:**
```
/server_age server_number:abc
→ "Invalid server number (digits only)"
```

**Server not found:**
```
/server_age server_number:99999999
→ "Could not find server age. Verify the number."
```

**Timeout:**
```
→ "Website took too long. Try again."
```

---

## That's It!

Just restart your bot and type:
```
/server_age server_number:1234
```

Done! 🚀

---

## For Your Server

Share with everyone:
> "Use `/server_age server_number:` followed by your state number to instantly check your server age!"

Example:
> `/server_age server_number:1234`

---

**Status: ✅ Ready!**

Restart bot → Command works → Enjoy! 💚
