import os
import time
import urllib.request

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/"
             "face_landmarker/face_landmarker/float16/1/face_landmarker.task")
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "face_landmarker.task")


class BlinkSwitch(QObject):
    """Acts like one switch: eyes closed for hold_seconds = one press."""
    selected = pyqtSignal()

    def __init__(self, hold_seconds=0.6, closed_threshold=0.5):
        super().__init__()
        self.hold_seconds = hold_seconds
        self.closed_threshold = closed_threshold
        self.closed_since = None
        self.fired = False

        if not os.path.exists(MODEL_PATH):
            print("Downloading face model (first run only)...")
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            raise RuntimeError("Camera not available")
        options = vision.FaceLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=MODEL_PATH),
            output_face_blendshapes=True,
        )
        self.detector = vision.FaceLandmarker.create_from_options(options)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(30)

    def tick(self):
        ok, frame = self.cap.read()
        if not ok:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = self.detector.detect(image)

        closed = False
        if result.face_blendshapes:
            scores = {s.category_name: s.score for s in result.face_blendshapes[0]}
            blink = (scores.get("eyeBlinkLeft", 0) + scores.get("eyeBlinkRight", 0)) / 2
            closed = blink > self.closed_threshold
        # no face found counts as "open", so nothing fires by accident

        now = time.time()
        if closed:
            if self.closed_since is None:
                self.closed_since = now
            elif not self.fired and now - self.closed_since >= self.hold_seconds:
                self.fired = True
                self.selected.emit()
        else:
            self.closed_since = None
            self.fired = False

    def stop(self):
        self.timer.stop()
        self.cap.release()
        self.detector.close()