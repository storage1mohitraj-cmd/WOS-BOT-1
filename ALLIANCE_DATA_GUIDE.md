# Alliance Data Integration Guide

This document explains how to set up and use the alliance data integration feature for the Discord bot.

## Setup Instructions

1. Create a Google Cloud Project:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project
   - Enable the Google Sheets API

2. Create Service Account:
   - In Google Cloud Console, go to "IAM & Admin" > "Service Accounts"
   - Create a new service account
   - Download the JSON key file
   - Rename it to `creds.json` and place it in the bot's root directory

3. Create Google Sheet:
   - Create a new Google Sheet
   - Add columns: Name | Rank | Active | Joined
   - Share the sheet with the service account email (give it viewer access)
   - Copy the Sheet ID from the URL (the long string between /d/ and /edit)

4. Configuration:
   - Copy `.env.template` to `.env`
   - Add your Google Sheet ID to `GOOGLE_SHEET_ID`
   - Add your OpenRouter API keys
   - (Optional) Add backup API keys for failover

## Sheet Format

The alliance data sheet should follow this format:

| Name | Rank | Active | Joined |
|------|------|--------|--------|
| Gina | R5 | Yes | 2023-01-01 |
| Hydra | R4 | Yes | 2023-02-15 |
| ... | ... | ... | ... |

- Name: Alliance member name
- Rank: R1, R2, R3, R4, or R5
- Active: "Yes" or "No"
- Joined: Date joined (YYYY-MM-DD format)

## Features

1. Dynamic Data Integration:
   - Alliance data is automatically fetched when needed
   - Data is cached for 5 minutes to reduce API calls
   - Automatic error handling and fallback to cached data

2. Smart Query Handling:
   - Bot can answer questions about alliance composition
   - Supports queries about ranks, activity, and membership
   - Data is efficiently formatted to avoid token limits

3. Example Queries:
   - "Who are the R5 members?"
   - "List all R4s"
   - "How many active members are there?"
   - "When did [member] join?"
   - "What's [member]'s rank?"

## Error Handling

The system includes robust error handling for:
- Missing credentials
- Network connectivity issues
- Invalid sheet format
- API rate limits
- Permission problems

Errors are logged for debugging, and the bot will continue functioning with cached data when possible.

## Maintenance

To keep the system running smoothly:

1. Regularly verify:
   - Service account credentials haven't expired
   - Sheet sharing permissions are correct
   - Bot has access to the sheet

2. Monitor:
   - API usage and rate limits
   - Sheet size and performance
   - Error logs for issues

3. Best Practices:
   - Keep the sheet organized and up-to-date
   - Remove inactive members regularly
   - Back up the credentials file
   - Review logs periodically

## Troubleshooting

Common issues and solutions:

1. Bot can't access sheet:
   - Check service account credentials
   - Verify sheet sharing permissions
   - Ensure GOOGLE_SHEET_ID is correct

2. Data not updating:
   - Clear the cache by restarting the bot
   - Check for sheet format issues
   - Verify network connectivity

3. High latency:
   - Review sheet size and complexity
   - Check API rate limits
   - Verify network performance