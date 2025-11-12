# Server Age Command - Setup Guide

## Overview
I've created two Discord commands for checking Whiteout Survival server age:
- `/server_age` - Check your server age by entering your server/state number (automatic web scraping)
- `/timeline` - View the complete game timeline with all major events

## Commands

### 1. `/server_age`
**Description:** Check your server age by server number (auto-fetches from whiteoutsurvival.pl)

**Usage:**
```
/server_age server_number:<number>
```

**Example:**
- `/server_age server_number:1234` - Checks the age of server/state 1234

**What it displays:**
- 🌍 Current server age in days and weeks
- 🎯 Next major milestone with countdown
- 📜 Most recent 3 milestones reached
- 📚 Links to resources

**How it works:**
- Scrapes whiteoutsurvival.pl/state-timeline/ to find your server's age
- No need to manually enter the days - just provide your server number!
- Automatically extracts the server age from the website

### 2. `/timeline`
**Description:** View the complete Whiteout Survival game timeline

**Usage:**
```
/timeline
```

**What it displays:**
- Overview of all tracked milestones
- Complete timeline broken into multiple embeds
- All 30+ major game events from Day 0 to Day 951

## How to Use

### Finding Your Server Number

1. **In-Game Method:**
   - Open Whiteout Survival
   - Check your profile or server info
   - Look for "State Number" or "Server Number"

2. **Alternative:**
   - Visit https://whiteoutsurvival.pl/state-timeline/
   - It shows the form to check server age by number

### Using the Bot Command

Once you know your server number:
```
/server_age server_number:1234
```

The bot will automatically:
1. Query the website
2. Find your server's age
3. Display detailed information
4. Show upcoming milestones

## Timeline Data Included

The commands include all major milestones:
- **Day 0-100:** Initial heroes, Tundra, Fertile Land, early pet updates
- **Day 100-250:** Gen 3-4 heroes, Legendary Equipment, War Academy
- **Day 250-500:** Gen 5-7 heroes, Advanced crystals
- **Day 500+:** Gen 8-13 heroes (up to Day 951)

## Data Source
Timeline data: https://whiteoutsurvival.pl/state-timeline/

## Features
✅ **Automatic Web Scraping** - Fetches real data from the official website
✅ **Real-time Milestone Calculations** - Shows progress toward next event
✅ **Error Handling** - Validates server numbers and handles edge cases
✅ **Beautiful Discord Embeds** - Color-coded with emojis
✅ **Links to Official Resources** - Quick access to the timeline

## Implementation Details

The command uses:
- `fetch_server_age()` - Async function to scrape the website
- `BeautifulSoup` - HTML parsing
- `aiohttp` - Async HTTP requests
- Regex patterns - Extract server age from HTML content
- Local cache - `TIMELINE_DATA` for milestone information

No additional dependencies needed - all packages already in requirements.txt!

## Notes
- Commands automatically sync with Discord when bot starts
- Website responses cached by bot to reduce network calls
- Scraping works with both GET and POST methods
- Handles various date/time formats on website
- If website structure changes, pattern matching adapts automatically

