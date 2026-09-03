# -*- coding: utf-8 -*-
"""
eye_control.py
===============
Aankhon se cursor control - webcam se chehra/aankh track karke mouse
cursor move karta hai, aur blink karne se click karta hai.

HONEST BAAT: Ye asli professional eye-tracker (jaise Tobii hardware) jitna
precise NAHI hoga. Woh dedicated infrared cameras aur calibration use karte
hain. Ye sirf normal webcam se "iris kis taraf hai" ka andaza laga ke cursor
move karta hai - isliye:
  - Thoda jittery/imprecise lagega, pixel-perfect nahi hoga
  - Achi lighting chahiye, chehra camera ke saamne seedha hona chahiye
  - Bahut fine/chhote targets (jaise chhote buttons) pe click karna mushkil hoga
  - Koi calibration step nahi hai abhi (agar accuracy chahiye, baad me add
    kar sakte hain - filhal ek general-purpose approximate version hai)

Chalane ke liye: mediapipe aur opencv-python chahiye.
"""

import threading
import time

try:
    import cv2
    import mediapipe as mp
    import numpy as np
    import pyautogui
except ImportError:
    cv2 = None
    mp = None
    np = None
    pyautogui = None

# ---- Tuning knobs - agar direction ulti lage ya bahut sensitive/insensitive
# lage, inhe badal sakte ho ----
INVERT_X = True     # True kiya kyunki "right dekhne par cursor left jaata tha"
INVERT_Y = True    # agar up/down bhi ulta lage, ise True kar do
GAIN = 3.5          # jitna zyada, utni chhoti aankh ki movement se poori screen cover
                    # hogi (face/head movement ka asar kam karne me bhi madad karta hai)


# Mediapipe FaceMesh (refine_landmarks=True) ke fixed landmark indices
LEFT_EYE_CORNERS = (33, 133)     # (bahar wala, andar wala)
LEFT_EYE_LIDS = (159, 145)       # (upar, neeche)
LEFT_IRIS_CENTER = 468

RIGHT_EYE_CORNERS = (362, 263)
RIGHT_EYE_LIDS = (386, 374)
RIGHT_IRIS_CENTER = 473

# Blink detect karne ke liye eye-aspect-ratio wale points
LEFT_EYE_EAR_POINTS = [33, 160, 158, 133, 153, 144]
RIGHT_EYE_EAR_POINTS = [362, 385, 387, 263, 373, 380]


def _eye_aspect_ratio(landmarks, points):
    p = [(landmarks[i].x, landmarks[i].y) for i in points]
    p = [np.array(pt) for pt in p]
    vertical1 = np.linalg.norm(p[1] - p[5])
    vertical2 = np.linalg.norm(p[2] - p[4])
    horizontal = np.linalg.norm(p[0] - p[3])
    if horizontal == 0:
        return 1.0
    return (vertical1 + vertical2) / (2.0 * horizontal)


def _gaze_ratio(landmarks, corners, lids, iris_idx):
    """Iris eye-socket ke andar kahan hai (0-1 ratio) - ye screen mapping
    ke liye base hai. Raw face-position se zyada reliable hai kyunki ye
    'aankh ke andar iris kaha hai' dekhta hai, poori face kaha hai wo nahi."""
    x_min = landmarks[corners[0]].x
    x_max = landmarks[corners[1]].x
    y_min = landmarks[lids[0]].y
    y_max = landmarks[lids[1]].y
    ix = landmarks[iris_idx].x
    iy = landmarks[iris_idx].y
    rx = (ix - x_min) / (x_max - x_min + 1e-6)
    ry = (iy - y_min) / (y_max - y_min + 1e-6)
    return rx, ry


class EyeCursorController:
    def __init__(self):
        self._running = False
        self._thread = None

    def available(self) -> bool:
        return cv2 is not None and mp is not None

    def start(self, voice=None):
        if not self.available():
            if voice:
                voice.speak("Eye tracking ke liye mediapipe aur opencv install nahi hai.")
            return
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        if voice:
            voice.speak("Eye cursor chalu kar diya. Chehra camera ke saamne rakhiye.")

    def stop(self, voice=None):
        self._running = False
        if voice:
            voice.speak("Eye cursor band kar diya.")

    def is_running(self) -> bool:
        return self._running

    def _run(self):
        mp_face_mesh = mp.solutions.face_mesh
        cam = cv2.VideoCapture(0)
        screen_w, screen_h = pyautogui.size()

        # Smoothing - taaki cursor jhatke se na kaanpe
        smooth_x, smooth_y = screen_w / 2, screen_h / 2
        SMOOTHING = 0.25

        blink_frames = 0
        BLINK_EAR_THRESHOLD = 0.19
        BLINK_CONSEC_FRAMES = 2
        last_click_time = 0.0

        try:
            with mp_face_mesh.FaceMesh(
                refine_landmarks=True, max_num_faces=1,
                min_detection_confidence=0.5, min_tracking_confidence=0.5,
            ) as face_mesh:
                while self._running:
                    ok, frame = cam.read()
                    if not ok:
                        time.sleep(0.05)
                        continue
                    frame = cv2.flip(frame, 1)
                    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = face_mesh.process(rgb)

                    if results.multi_face_landmarks:
                        lm = results.multi_face_landmarks[0].landmark

                        # --- dono aankhon ka gaze ratio average karo ---
                        rx_l, ry_l = _gaze_ratio(lm, LEFT_EYE_CORNERS, LEFT_EYE_LIDS, LEFT_IRIS_CENTER)
                        rx_r, ry_r = _gaze_ratio(lm, RIGHT_EYE_CORNERS, RIGHT_EYE_LIDS, RIGHT_IRIS_CENTER)
                        rx = (rx_l + rx_r) / 2.0
                        ry = (ry_l + ry_r) / 2.0

                        # GAIN: center (0.5) ke aas-paas ki chhoti movement ko
                        # amplify karte hain, taaki halki si pupil movement se
                        # poori screen cover ho sake (aur bade head-movement
                        # ka effect proportionally kam mehsoos ho).
                        rx = 0.5 + (rx - 0.5) * GAIN
                        ry = 0.5 + (ry - 0.5) * GAIN
                        rx = min(max(rx, 0.0), 1.0)
                        ry = min(max(ry, 0.0), 1.0)

                        if INVERT_X:
                            rx = 1.0 - rx
                        if INVERT_Y:
                            ry = 1.0 - ry

                        target_x = rx * screen_w
                        target_y = ry * screen_h

                        smooth_x += (target_x - smooth_x) * SMOOTHING
                        smooth_y += (target_y - smooth_y) * SMOOTHING

                        try:
                            pyautogui.moveTo(int(smooth_x), int(smooth_y), duration=0)
                        except Exception:
                            pass

                        # --- blink -> click ---
                        left_ear = _eye_aspect_ratio(lm, LEFT_EYE_EAR_POINTS)
                        right_ear = _eye_aspect_ratio(lm, RIGHT_EYE_EAR_POINTS)
                        avg_ear = (left_ear + right_ear) / 2.0

                        if avg_ear < BLINK_EAR_THRESHOLD:
                            blink_frames += 1
                        else:
                            if blink_frames >= BLINK_CONSEC_FRAMES:
                                now = time.time()
                                if now - last_click_time > 0.8:  # accidental double-click na ho
                                    try:
                                        pyautogui.click()
                                    except Exception:
                                        pass
                                    last_click_time = now
                            blink_frames = 0

                    time.sleep(0.01)
        except Exception as e:
            print(f"[eye_control error: {e}]")
        finally:
            cam.release()
