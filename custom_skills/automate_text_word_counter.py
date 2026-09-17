import pyperclip
import re

def execute(context: dict = None) -> dict:
    '''
    Analyzes the text currently present in the system clipboard.
    Provides word count, character count (with and without spaces), and sentence count.
    
    Returns:
        dict: {"success": bool, "message": str, "data": dict}
    '''
    try:
        # Step 1: Fetch text from clipboard
        # Jarvis uses the clipboard as the primary input source for desktop text automation
        input_text = pyperclip.paste()

        if not input_text or input_text.strip() == "":
            return {
                "success": False, 
                "message": "Clipboard khali hai! Pehle kuch text copy karo fir mujhe batao.", 
                "data": None
            }

        # Step 2: Perform Analysis
        # Remove leading/trailing whitespace for accurate measurement
        clean_text = input_text.strip()

        # Word Count: Using regex to find word boundaries
        words = re.findall(r'\b\w+\b', clean_text)
        word_count = len(words)

        # Character Count (With Spaces)
        char_count_with_spaces = len(clean_text)

        # Character Count (Without Spaces/Newlines)
        char_count_no_spaces = len(re.sub(r'\s+', '', clean_text))

        # Sentence Count: Looking for . ! or ?
        sentences = re.findall(r'[.!?]+', clean_text)
        sentence_count = len(sentences) if len(sentences) > 0 else 1
        # If there is text but no punctuation, it's at least 1 sentence/block
        if len(clean_text) > 0 and len(sentences) == 0:
            sentence_count = 1

        # Step 3: Prepare Result Data
        analysis_results = {
            "word_count": word_count,
            "character_count_with_spaces": char_count_with_spaces,
            "character_count_no_spaces": char_count_no_spaces,
            "sentence_count": sentence_count,
            "text_preview": clean_text[:100] + "..." if len(clean_text) > 100 else clean_text
        }

        # Step 4: Generate Hinglish confirmation message
        # Example: "Analysis complete! Total 120 words aur 850 characters mile hain."
        message = (
            f"Text analyze kar liya gaya hai! "
            f"Total {word_count} words aur {char_count_with_spaces} characters mile hain."
        )

        return {
            "success": True,
            "message": message,
            "data": analysis_results
        }

    except ImportError:
        return {
            "success": False,
            "message": "Pyperclip library missing hai. Please install it using 'pip install pyperclip'.",
            "data": None
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Automation mein kuch error aa gaya: {str(e)}",
            "data": None
        }

if __name__ == "__main__":
    # Local testing block
    import sys
    print("Running local test...")
    # Simulate clipboard content if needed or just run
    result = execute()
    print(f"Result: {result}")