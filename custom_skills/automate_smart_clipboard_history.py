import sqlite3
import pyperclip
import pyautogui
import os
import time
from datetime import datetime

def execute(context: dict = None) -> dict:
    # Guardrail: Enforce PyAutoGUI safety boundaries
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.2
    '''
    Automates Smart Clipboard History:
    - Syncs current clipboard to a local SQLite database.
    - Maintains only the last 20 unique snippets.
    - Allows searching through history.
    - Allows pasting a specific historical snippet.
    
    Context Keys:
    - 'query': (str) Search for keywords in history.
    - 'paste_id': (int) The ID of the history item to paste.
    '''
    db_path = os.path.join(os.getcwd(), "clipboard_history.db")
    context = context or {}
    
    try:
        # 1. Database Initialization
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clipboard_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                timestamp DATETIME NOT NULL
            )
        ''')
        conn.commit()

        # 2. Sync: Capture current clipboard and update DB
        current_clip = pyperclip.paste().strip()
        
        if current_clip:
            # Check the last entry to avoid duplicates
            cursor.execute("SELECT content FROM clipboard_history ORDER BY id DESC LIMIT 1")
            last_entry = cursor.fetchone()
            
            if not last_entry or last_entry[0] != current_clip:
                cursor.execute(
                    "INSERT INTO clipboard_history (content, timestamp) VALUES (?, ?)",
                    (current_clip, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                )
                conn.commit()
                
                # Maintain only the last 20 items
                cursor.execute('''
                    DELETE FROM clipboard_history WHERE id NOT IN (
                        SELECT id FROM clipboard_history ORDER BY id DESC LIMIT 20
                    )
                ''')
                conn.commit()

        # 3. Logic: Search or Paste
        query = context.get('query')
        paste_id = context.get('paste_id')

        if paste_id is not None:
            # Action: Paste specific item
            cursor.execute("SELECT content FROM clipboard_history WHERE id = ?", (paste_id,))
            result = cursor.fetchone()
            
            if result:
                content_to_paste = result[0]
                pyperclip.copy(content_to_paste)
                # Small delay to ensure clipboard is ready
                time.sleep(0.1)
                pyautogui.hotkey('ctrl', 'v')
                conn.close()
                return {
                    "success": True, 
                    "message": f"Purana snippet (ID: {paste_id}) successfully paste kar diya gaya hai.", 
                    "data": {"id": paste_id, "content": content_to_paste}
                }
            else:
                conn.close()
                return {"success": False, "message": f"ID {paste_id} wala koi snippet history mein nahi mila.", "data": None}

        elif query:
            # Action: Search
            cursor.execute(
                "SELECT id, content, timestamp FROM clipboard_history WHERE content LIKE ? ORDER BY id DESC",
                ('%' + query + '%',)
            )
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "content": row[1],
                    "timestamp": row[2]
                })
            
            conn.close()
            if results:
                return {
                    "success": True, 
                    "message": f"'{query}' ke liye {len(results)} matches mil gaye hain.", 
                    "data": results
                }
            else:
                return {
                    "success": True, 
                    "message": f"'{query}' ke liye koi results nahi mile.", 
                    "data": []
                }

        else:
            # Default: Just Sync
            conn.close()
            return {
                "success": True, 
                "message": "Clipboard history sync ho gayi hai aur latest snippet save kar liya gaya hai.", 
                "data": None
            }

    except Exception as e:
        try:
            if 'conn' in locals():
                conn.close()
        except:
            pass
        return {
            "success": False, 
            "message": f"Clipboard automation mein error aaya: {str(e)}", 
            "data": None
        }