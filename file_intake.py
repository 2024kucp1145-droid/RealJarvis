import os


class FileIntake:
    """User ki dropped file ko read karke AI context banata hai."""

    MAX_CHARS = 12000

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.extension = os.path.splitext(filepath)[1].lower()
        self.is_image = self.extension in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
        self.is_video = self.extension in (".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".3gp", ".mpeg", ".mpg")
        self.is_folder = os.path.isdir(filepath)
        self.content = self._extract()

    def _extract(self) -> str:
        if not os.path.exists(self.filepath):
            return "(file nahi mili)"

        # ---- Folder ----
        if self.is_folder:
            try:
                items = []
                for root, dirs, files in os.walk(self.filepath):
                    level = root.replace(self.filepath, '').count(os.sep)
                    indent = '  ' * level
                    items.append(f"{indent}{os.path.basename(root)}/")
                    subindent = '  ' * (level + 1)
                    for f in files[:30]:  # per folder limit
                        fp = os.path.join(root, f)
                        size = os.path.getsize(fp)
                        size_str = f"{size} bytes" if size < 1024 else f"{size//1024} KB" if size < 1024*1024 else f"{size//(1024*1024)} MB"
                        items.append(f"{subindent}{f} ({size_str})")
                    if len(items) > 150:  # total hard limit
                        items.append("... (aur bahut saari files)")
                        break
                return "\n".join(items) if items else "(khali folder)"
            except Exception as e:
                return f"(folder read error: {e})"

        # ---- Images ----
        if self.is_image:
            return "(IMAGE_FILE)"

        # ---- Videos ----
        if self.is_video:
            return "(VIDEO_FILE)"

        # ---- Plain text files ----
        if self.extension in (".txt", ".md", ".py", ".json", ".csv", ".html", ".css", ".js", ".xml", ".log", ".ini", ".cfg"):
            try:
                with open(self.filepath, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception as e:
                return f"(file read error: {e})"

        # ---- PDF ----
        if self.extension == ".pdf":
            try:
                import PyPDF2
                text = ""
                with open(self.filepath, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() or ""
                return text or "(PDF mein text nahi mila)"
            except ImportError:
                return "(PDF read karne ke liye PyPDF2 install karo)"
            except Exception as e:
                return f"(PDF error: {e})"

        # ---- Word DOCX ----
        if self.extension == ".docx":
            try:
                import docx
                doc = docx.Document(self.filepath)
                return "\n".join([p.text for p in doc.paragraphs])
            except ImportError:
                return "(DOCX read karne ke liye python-docx install karo)"
            except Exception as e:
                return f"(DOCX error: {e})"

        # ---- Excel ----
        if self.extension in (".xlsx", ".xls"):
            try:
                import pandas as pd
                df = pd.read_excel(self.filepath)
                return df.to_string(index=False)
            except ImportError:
                return "(Excel read karne ke liye pandas+openpyxl install karo)"
            except Exception as e:
                return f"(Excel error: {e})"

        return "(is file type ka support abhi nahi hai. TXT, PDF, DOCX, Excel, Images, Videos, Folders support hain.)"

    def build_prompt(self, user_question: str) -> str:
        """AI ke liye prompt banata hai — file content + user question."""
        if self.is_image:
            return user_question

        truncated = self.content[:self.MAX_CHARS]
        file_type = "folder" if self.is_folder else "file"
        return (
            f"User ne ek {file_type} di hai: '{self.filename}'\n\n"
            f"{file_type.capitalize()} ka content:\n{'='*40}\n{truncated}\n{'='*40}\n\n"
            f"User ka sawaal: {user_question}\n\n"
            f"IMPORTANT: Sirf upar diye gaye content ka use karke jawab do. "
            f"Agar jawab content mein nahi hai, saaf keh do 'is {file_type} mein ye jaankari nahi hai'."
        )

    def is_valid(self) -> bool:
        if self.is_image or self.is_video or self.is_folder:
            return True
        return bool(self.content) and not self.content.startswith("(")