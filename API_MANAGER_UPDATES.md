"""
Instructions for updating the api_manager.py file:

1. Update imports to include new functions:
   ```python
   from sheets_manager import SheetsManager, is_event_related_query
   ```

2. Update the RobustOpenRouterManager class init:
   ```python
   def __init__(self, api_keys: List[str], spreadsheet_id: str = None):
       self.api_keys = api_keys
       self.current_key_index = 0
       self.spreadsheet_id = spreadsheet_id
       self.sheets_manager = SheetsManager()
   ```

3. Modify the make_request function:
   ```python
   async def make_request(messages: List[Dict[str, str]], max_tokens: int = 1000, include_sheet_data: bool = True) -> str:
       if include_sheet_data and messages and messages[0]['role'] == 'system':
           if not manager.spreadsheet_id:
               logger.error("GOOGLE_SHEET_ID is not set in .env file")
               return await manager.make_request(messages, max_tokens)
               
           try:
               # Get user's question (last message in the conversation)
               user_question = messages[-1]['content'] if messages[-1]['role'] == 'user' else ''
               
               # Determine which sheet to use based on the question
               sheet_name = 'Event Guides' if is_event_related_query(user_question) else 'Members'
               logger.info(f"Using sheet: {sheet_name} for query \"{user_question}\"")
               
               # Fetch sheet data
               sheet_data = await manager.sheets_manager.fetch_sheet_data(manager.spreadsheet_id, sheet_name)
               
               if not sheet_data:
                   error_msg = "⚠️ No event data found. Try updating the sheet." if sheet_name == "Event Guides" else \
                             "⚠️ No member data available right now."
                   logger.warning(f"No data retrieved from sheet: {sheet_name}")
                   return error_msg
               
               # Format the data based on sheet type
               if sheet_name == 'Members':
                   # Filter and format member data
                   filtered_data = filter_sheet_data(user_question, sheet_data)
                   formatted_messages = format_alliance_data(filtered_data, user_question)
                   
                   if len(formatted_messages) == 1:
                       # Single message - inject it into system message
                       alliance_text = formatted_messages[0]
                       system_msg = messages[0]
                       system_msg['content'] = f"{system_msg['content']}\n\nCurrent Alliance Data:\n{alliance_text}"
                       messages[0] = system_msg
                       logger.info("Injected single alliance message into prompt")
                       return await manager.make_request(messages, max_tokens)
                   else:
                       # Multiple messages - return special format for multi-message handling
                       logger.info(f"Alliance data split into {len(formatted_messages)} messages")
                       return "ALLIANCE_MESSAGES:" + json.dumps(formatted_messages)
               else:
                   # Format event data
                   event_text = manager.sheets_manager.format_sheet_data_for_prompt(sheet_data, sheet_name)
                   system_msg = messages[0]
                   system_msg['content'] = f"{system_msg['content']}\n\nEvent Information:\n{event_text}"
                   messages[0] = system_msg
                   logger.info("Injected event guide data into prompt")
                   return await manager.make_request(messages, max_tokens)
                   
           except Exception as e:
               logger.error(f"Failed to inject sheet data: {str(e)}", exc_info=True)
       
       return await manager.make_request(messages, max_tokens)
   ```

These changes will:
1. Support both member and event data fetching
2. Log which sheet is being used for each query
3. Handle different data formats appropriately
4. Provide clear error messages for missing data
5. Maintain the multi-message support for alliance data