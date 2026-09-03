# -*- coding: utf-8 -*-
"""
setup_face.py
=============
Ek baar chalao - webcam se tumhari photo lekar 'data/owner_face.jpg' me save
kar dega. Isi photo se aage face verification hoga.

Chalane ka tareeka:
    python setup_face.py
"""

import os
import cv2
import config


def main():
    os.makedirs(os.path.dirname(config.FACE_DATA_PATH), exist_ok=True)
    cam = cv2.VideoCapture(0)
    print("Camera khul raha hai... 'SPACE' dabao photo lene ke liye, 'ESC' se cancel.")

    while True:
        ok, frame = cam.read()
        if not ok:
            print("Camera se frame nahi mil raha.")
            break
        cv2.imshow("Jarvis - Face Setup (SPACE = capture, ESC = cancel)", frame)
        key = cv2.waitKey(1)
        if key % 256 == 27:  # ESC
            print("Cancel kar diya.")
            break
        elif key % 256 == 32:  # SPACE
            cv2.imwrite(config.FACE_DATA_PATH, frame)
            print(f"Photo save ho gayi: {config.FACE_DATA_PATH}")
            break

    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
