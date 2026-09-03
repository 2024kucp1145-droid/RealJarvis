# -*- coding: utf-8 -*-
"""
auth.py
=======
Login flow: Jarvis intro deta hai, phir ek popup box (GUI) me password
type karke dena hota hai. Sahi hone par login ho jaata hai.
"""

import os
import config


def verify_password_gui(gui) -> bool:
    """GUI popup box se password poochta hai."""
    if gui is None:
        return False
    pw = gui.ask_password()
    return config.verify_password(pw) if pw else False


def verify_face() -> bool:
    try:
        import cv2
        import face_recognition
    except ImportError:
        print("[face_recognition/opencv install nahi hai - face check skip]")
        return False

    if not os.path.exists(config.FACE_DATA_PATH):
        print("[owner_face.jpg nahi mili - pehle setup_face.py chalao]")
        return False

    known_image = face_recognition.load_image_file(config.FACE_DATA_PATH)
    known_encodings = face_recognition.face_encodings(known_image)
    if not known_encodings:
        print("[saved photo me chehra detect nahi hua]")
        return False
    known_encoding = known_encodings[0]

    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("[Webcam open nahi ho saka - camera check bypass/fail]")
        return False

    matched = False
    try:
        for _ in range(30):
            ok, frame = cam.read()
            if not ok or frame is None:
                continue
            rgb = frame[:, :, ::-1]
            locations = face_recognition.face_locations(rgb)
            encodings = face_recognition.face_encodings(rgb, locations)
            for enc in encodings:
                result = face_recognition.compare_faces([known_encoding], enc, tolerance=0.5)
                if result and result[0]:
                    matched = True
                    break
            if matched:
                break
    except Exception as e:
        print(f"[face verify error: {e}]")
    finally:
        cam.release()
    return matched


def authenticate(voice, gui=None) -> bool:
    """Poora login flow. True/False return karta hai."""
    password_ok = verify_password_gui(gui)
    if not password_ok:
        return False

    if config.FACE_VERIFICATION_ENABLED:
        voice.speak("Ab apna chehra camera ke saamne rakhiye.")
        face_ok = verify_face()
        if config.AUTH_MODE == "both" and not face_ok:
            return False

    return True
