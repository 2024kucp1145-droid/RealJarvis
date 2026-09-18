import os
import shutil
import sys
from pathlib import Path

def execute(context: dict = None) -> dict:
    """
    Automates intelligent disk junk cleaning by targeting temporary directories 
    and browser caches safely.
    
    Returns:
        {"success": bool, "message": str, "data": dict}
    """
    
    # List of target directories to clean (Whitelisted for safety)
    # We target the contents of these folders, not the folders themselves, 
    # to avoid breaking application structures.
    target_paths = []
    
    # 1. User Temp Directory (%TEMP%)
    user_temp = os.environ.get('TEMP')
    if user_temp:
        target_paths.append(Path(user_temp))
        
    # 2. Windows System Temp Directory
    system_temp = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'Temp')
    target_paths.append(Path(system_temp))
    
    # 3. Chrome Cache (Common Path)
    local_app_data = os.environ.get('LOCALAPPDATA')
    if local_app_data:
        chrome_cache = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "Default" / "Cache"
        if chrome_cache.exists():
            target_paths.append(chrome_cache)
            
        edge_cache = Path(local_app_data) / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache"
        if edge_cache.exists():
            target_paths.append(edge_cache)

    total_files_removed = 0
    total_space_cleared_bytes = 0
    errors = []

    def get_size(path: Path) -> int:
        """Calculate size of a file or directory in bytes."""
        try:
            if path.is_file():
                return path.stat().st_size
            elif path.is_dir():
                return sum(f.stat().st_size for f in path.glob('**/*') if f.is_file())
            return 0
        except Exception:
            return 0

    try:
        for base_path in target_paths:
            if not base_path.exists():
                continue
                
            # Iterate through items inside the target directory
            try:
                for item in base_path.iterdir():
                    try:
                        item_size = get_size(item)
                        
                        if item.is_file() or item.is_symlink():
                            item.unlink()
                            total_files_removed += 1
                            total_space_cleared_bytes += item_size
                        elif item.is_dir():
                            shutil.rmtree(item)
                            total_files_removed += 1
                            total_space_cleared_bytes += item_size
                            
                    except (PermissionError, OSError):
                        # File is likely in use by another process (very common in Temp)
                        # We skip these gracefully to ensure "Intelligent" cleaning.
                        continue
                    except Exception as e:
                        errors.append(f"Error deleting {item.name}: {str(e)}")
            except Exception as e:
                errors.append(f"Error accessing {base_path}: {str(e)}")

        # Convert bytes to MB for the user message
        space_mb = round(total_space_cleared_bytes / (1024 * 1024), 2)
        
        # Constructing the Hinglish message
        if total_files_removed > 0:
            message = f"Disk safai complete! Total {total_files_removed} files delete ki gayi aur approximately {space_mb} MB space bachayi gayi."
        else:
            message = "Disk clean karne ki koshish ki, par koi junk file nahi mili ya files currently in use hain."

        return {
            "success": True,
            "message": message,
            "data": {
                "files_removed": total_files_removed,
                "space_cleared_mb": space_mb,
                "errors": errors
            }
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Disk cleaning process mein error aaya: {str(e)}",
            "data": {"error": str(e)}
        }

if __name__ == "__main__":
    # Local testing
    print(execute())