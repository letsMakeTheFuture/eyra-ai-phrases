"""Blink switch using plain OpenCV image processing.

No AI model is used here: no MediaPipe, no Haar cascades, no neural network.
The helper draws a box around ONE eye once at start-up. During setup the
program measures the box with five simple image measures (contrast,
brightness, dark-pixel share, edges, sharpness) while the eye is open and
while it is closed, then automatically keeps the measure that separates the
two states best. Holding the eye closed for `hold_seconds` fires the
`selected` signal.

Limits: the camera and the head must stay roughly fixed after setup, and the
lighting should be steady. Restart the app to calibrate again.
"""
import time

import cv2
import numpy as np
from PyQt5.QtCore import QObject, QTimer, pyqtSignal

DEBUG = False         # prints the live numbers twice per second
FRAME_MS = 33         # about 30 frames per second
MIN_SEPARATION = 1.0  # how clearly open and closed must differ


def _beep(freq):
    """Short beep so the user knows what to do without reading the screen."""
    try:
        import winsound
        winsound.Beep(freq, 250)
    except Exception:
        pass


def _features(frame, box):
    """Simple measures of the eye box. No model, only pixel arithmetic."""
    x, y, w, h = box
    roi = frame[y:y + h, x:x + w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, (80, 40))
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    g = gray.astype(np.float32)
    mean = float(np.mean(g))
    sobel_y = cv2.Sobel(g, cv2.CV_32F, 0, 1, ksize=3)
    return {
        "contrast": float(np.std(g)),
        "brightness": mean,
        "dark_share": float(np.mean(g < 0.6 * mean)) * 100.0,
        "edges": float(np.mean(np.abs(sobel_y))),
        "sharpness": float(np.var(cv2.Laplacian(g, cv2.CV_32F))) ** 0.5,
    }


class BlinkSwitch(QObject):
    selected = pyqtSignal()

    def __init__(self, camera=0, hold_seconds=0.7):
        super().__init__()
        self.hold_seconds = hold_seconds
        self.metric = "contrast"
        self.closed_is_lower = True
        self.cap = cv2.VideoCapture(camera, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            raise RuntimeError("Camera not available")

        for _ in range(10):                      # let the camera warm up
            self._read()

        self.box = self._choose_box()
        self.threshold = self._calibrate()

        self.recent = []
        self.closed_since = None
        self.armed = True
        self.last_debug = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(FRAME_MS)

    # ---- camera helpers ----
    def _read(self):
        ok, frame = self.cap.read()
        if not ok:
            return None
        return cv2.flip(frame, 1)                # mirror, like a selfie

    def _choose_box(self):
        frame = None
        while frame is None:
            frame = self._read()
        name = "Draw a TIGHT box around ONE eye only, then press ENTER"
        box = cv2.selectROI(name, frame, showCrosshair=False)
        cv2.destroyAllWindows()
        cv2.waitKey(1)
        if box[2] < 10 or box[3] < 10:
            self.cap.release()
            raise RuntimeError("No eye box chosen")
        return tuple(int(v) for v in box)

    def _collect(self, message, seconds=2.0, grace=1.0):
        """Show a message to the helper and measure the eye box for a while."""
        runs = []
        start = time.time()
        while time.time() - start < grace + seconds:
            frame = self._read()
            if frame is None:
                continue
            elapsed = time.time() - start
            x, y, w, h = self.box
            shown = frame.copy()
            cv2.rectangle(shown, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(shown, message, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        1.0, (0, 255, 255), 2)
            cv2.imshow("EYRA eye setup", shown)
            cv2.waitKey(1)
            if elapsed >= grace:
                runs.append(_features(frame, self.box))
        return runs

    def _calibrate(self):
        _beep(800)    # medium beep: keep your eyes OPEN
        open_runs = self._collect("Keep the eye OPEN, look at the screen")
        _beep(1400)   # high beep: CLOSE your eyes and keep them closed
        closed_runs = self._collect(
            "Now CLOSE the eyes and keep them closed", grace=1.5)
        _beep(500)    # low beep: open your eyes, setup is done
        cv2.destroyAllWindows()
        cv2.waitKey(1)

        if not open_runs or not closed_runs:
            self.cap.release()
            raise RuntimeError("No camera frames during setup")

        best = None
        for name in open_runs[0]:
            o = np.array([f[name] for f in open_runs])
            c = np.array([f[name] for f in closed_runs])
            mo, mc = float(o.mean()), float(c.mean())
            score = abs(mo - mc) / (float(o.std()) + float(c.std()) + 1e-6)
            print(f"Calibration {name}: open={mo:.2f} closed={mc:.2f} "
                  f"separation={score:.2f}")
            if best is None or score > best[0]:
                best = (score, name, mo, mc)

        score, name, mo, mc = best
        if score < MIN_SEPARATION:
            self.cap.release()
            raise RuntimeError(
                "Could not tell open from closed eyes. Did you close your "
                "eyes after the HIGH beep? Use steady light, move closer, "
                "draw the box tight around one eye, and retry")
        self.metric = name
        self.closed_is_lower = mc < mo
        print(f"Using '{name}' (separation {score:.2f})")
        return (mo + mc) / 2

    # ---- main loop ----
    def tick(self):
        frame = self._read()
        if frame is None:
            return
        value = _features(frame, self.box)[self.metric]
        self.recent = (self.recent + [value])[-3:]       # smooth 3 frames
        level = sum(self.recent) / len(self.recent)
        now = time.time()

        if self.closed_is_lower:
            closed = level < self.threshold
        else:
            closed = level > self.threshold

        if DEBUG and now - self.last_debug > 0.5:
            print(f"{self.metric}={level:.2f} "
                  f"threshold={self.threshold:.2f} closed={closed}")
            self.last_debug = now

        if closed:
            if self.closed_since is None:
                self.closed_since = now
            elif self.armed and now - self.closed_since >= self.hold_seconds:
                self.armed = False       # must reopen before the next select
                self.selected.emit()
        else:
            self.closed_since = None
            self.armed = True

    def stop(self):
        self.timer.stop()
        if self.cap.isOpened():
            self.cap.release()