"""
Instructions for updating the sheets_manager.py file:

1. Update imports at top:
   ```python
   from typing import List, Dict, Any, Optional, Union
   ```

2. Add is_event_related_query function before SheetsManager class:
   ```python
   def is_event_related_query(question: str) -> bool:
       event_keywords = [
           'event', 'guide', 'rewards', 'tips', 'strategy', 'how to',
           'what is', 'explain', 'help with', 'about the'
       ]
       return any(keyword in question.lower() for keyword in event_keywords)
   ```

3. Update SheetsManager class initialization:
   ```python
   def __init__(self, creds_file: str = 'creds.json', cache_duration: int = 300):
       self.creds_file = creds_file
       self.service = None
       self.cache = {}  # Dictionary to store data from different sheets
       self.last_fetch = {}  # Track last fetch time per sheet
       self.cache_duration = cache_duration
       self._init_service()
   ```

4. Modify reset_cache method:
   ```python
   def reset_cache(self):
       self.cache = {}
       self.last_fetch = {}
       logger.info("Sheet cache reset successfully")
   ```

5. Add _is_cache_valid method:
   ```python
   def _is_cache_valid(self, sheet_name: str) -> bool:
       if sheet_name not in self.last_fetch:
           return False
       return (time.time() - self.last_fetch[sheet_name]) < self.cache_duration
   ```

6. Replace get_alliance_data with fetch_sheet_data:
   ```python
   async def fetch_sheet_data(self, spreadsheet_id: str, sheet_name: str = 'Members') -> List[Dict[str, Any]]:
       if self._is_cache_valid(sheet_name) and sheet_name in self.cache:
           return self.cache[sheet_name]
       
       try:
           result = self.service.spreadsheets().values().get(
               spreadsheetId=spreadsheet_id,
               range=f"{sheet_name}!A:Z"
           ).execute()
           
           rows = result.get('values', [])
           if not rows:
               return []
           
           headers = [h.strip() for h in rows[0]]
           data = []
           
           for row in rows[1:]:
               row_data = row + [''] * (len(headers) - len(row))
               row_dict = {}
               
               for i, header in enumerate(headers):
                   value = row_data[i].strip() if i < len(row_data) else ''
                   
                   if sheet_name == 'Members':
                       if header == 'Active':
                           value = value.lower() in ['yes', 'true', '1', 'active']
                       elif header == 'State':
                           value = '3063'
                       elif header == 'Rank':
                           value = value.upper() if value else ''
                   
                   row_dict[header] = value
               
               if sheet_name == 'Members':
                   if not row_dict.get('Name') or not row_dict.get('Rank') or \
                      row_dict['Rank'] not in ['R1', 'R2', 'R3', 'R4', 'R5']:
                       continue
               else:  # Event Guides
                   if not row_dict.get('Event Name') or not row_dict.get('Description'):
                       continue
               
               data.append(row_dict)
           
           self.cache[sheet_name] = data
           self.last_fetch[sheet_name] = time.time()
           return data
           
       except Exception as e:
           logger.error(f"Error fetching {sheet_name} data: {e}")
           return self.cache.get(sheet_name, [])
   ```

7. Add format_sheet_data_for_prompt method:
   ```python
   def format_sheet_data_for_prompt(self, data: List[Dict[str, Any]], sheet_name: str) -> str:
       if not data:
           return f"No {sheet_name.lower()} data available."
       
       if sheet_name == 'Members':
           df = pd.DataFrame(data)
           total_members = len(df)
           active_members = df['Active'].sum()
           inactive_members = total_members - active_members
           
           ranks = df['Rank'].value_counts().sort_index()
           sections = []
           
           summary = [
               "📊 ALLIANCE STATISTICS:",
               f"• Total Members: {total_members}",
               f"• Active Members: {active_members}",
               f"• Inactive Members: {inactive_members}",
               "• Rank Distribution:"
           ]
           
           for rank, count in ranks.items():
               active_in_rank = len(df[(df['Rank'] == rank) & (df['Active'])])
               summary.append(f"  - {rank}: {count} members ({active_in_rank} active)")
           
           sections.append("\n".join(summary))
           return "\n\n".join(sections)
           
       else:  # Event Guides
           sections = ["📖 EVENT GUIDES:"]
           for event in data:
               sections.append(
                   f"• {event.get('Event Name', 'Unknown Event')}\n" +
                   f"  {event.get('Description', 'No description available')}\n" +
                   (f"  Tips: {event.get('Tips', 'No tips available')}" if event.get('Tips') else "")
               )
           return "\n\n".join(sections)
   ```

These changes will:
1. Support both Members and Event Guides sheets
2. Cache data separately for each sheet
3. Format data appropriately based on sheet type
4. Default state to 3063 for all members
5. Handle sheet-specific validation rules
6. Provide clear error messages for missing data