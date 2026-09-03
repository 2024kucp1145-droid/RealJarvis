import os
import shutil
from pathlib import Path

def execute(context: dict = None) -> dict:
    try:
        desktop_path = Path.home() / "Desktop"
        if not desktop_path.exists():
            return {"success": False, "message": "Mujhe aapka Desktop folder nahi mila."}
            
        target_folder = desktop_path / "Desktop_Images"
        target_folder.mkdir(exist_ok=True)
        
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
        count = 0
        
        for file_path in desktop_path.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in image_extensions:
                shutil.copy(file_path, target_folder / file_path.name)
                count += 1
                
        if count == 0:
            return {"success": True, "message": "Desktop par koi bhi image nahi mili."}
            
        return {
            "success": True,
            "message": f"Maine desktop ki sabhi {count} images ko 'Desktop_Images' naam ke folder me save kar diya hai.",
            "data": {"count": count, "folder": str(target_folder)}
        }
    except Exception as e:
        return {"success": False, "message": f"Images collect karne me kuch dikkat aa gayi: {str(e)}"}