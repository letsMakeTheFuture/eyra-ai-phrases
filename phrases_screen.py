import sys
import pyttsx3
from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QLabel,
                             QPushButton, QLineEdit)

from phrase_provider import MockProvider

try:
    from muse_provider import MuseSparkProvider
    PRIMARY = MuseSparkProvider()
except Exception as e:
    print("Meta model unavailable, using labeled mock:", e)
    PRIMARY = None

try:
    from eye_switch import BlinkSwitch
except Exception as e:
    print("Eye input unavailable:", e)
    BlinkSwitch = None

SCAN_MS = 1200

SITUATIONS = [
    ("I need help", "HELP"),
    ("I am in pain", "PAIN"),
    ("I need something", "NEED"),
]

IDLE = ("font-size:30pt; padding:22px; color:#94A3B8; background:#1C2128;"
        "border:2px solid #334155; border-radius:25px;")
ACTIVE = ("font-size:30pt; padding:22px; color:white; background:#0369A1;"
          "border:8px solid #50C878; border-radius:25px;")
INPUT = ("font-size:18pt; padding:10px; color:#E2E8F0; background:#161B22;"
         "border:2px solid #4169E1; border-radius:12px;")


class PhraseWorker(QThread):
    done = pyqtSignal(list, str)  # phrases, source label

    def __init__(self, mode, text, context, code=""):
        super().__init__()
        self.mode, self.text, self.context, self.code = mode, text, context, code

    def run(self):
        if PRIMARY:
            try:
                if self.mode == "answer":
                    phrases = PRIMARY.answer(self.text, self.context)
                else:
                    phrases = PRIMARY.suggest(self.text, self.context)
                self.done.emit(phrases, PRIMARY.name)
                return
            except Exception as e:
                print("AI request failed:", e)
        mock = MockProvider()
        if self.mode == "answer":
            self.done.emit(mock.answer(self.text, self.context), mock.name)
        else:
            self.done.emit(mock.suggest(self.code, self.context), mock.name)


class Speaker(QThread):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.say(self.text)
        engine.runAndWait()
        engine.stop()


class PhrasesWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EYRA AI Phrases")
        self.setStyleSheet("background-color:#0A0F14;")
        self.setFocusPolicy(Qt.StrongFocus)

        root = QVBoxLayout(self)

        self.context_box = QLineEdit()
        self.context_box.setPlaceholderText(
            "Caregiver (optional): where are we, who is here? Press Enter to save")
        self.context_box.setStyleSheet(INPUT)
        self.context_box.editingFinished.connect(self.setFocus)

        self.title = QLabel()
        self.title.setWordWrap(True)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("color:#50C878; font-size:30pt; font-weight:bold;")
        self.source = QLabel()
        self.source.setAlignment(Qt.AlignCenter)

        self.question_box = QLineEdit()
        self.question_box.setPlaceholderText(
            "Caregiver: type what was asked, then press Enter")
        self.question_box.setStyleSheet(INPUT)
        self.question_box.returnPressed.connect(self.ask)
        self.question_box.hide()

        self.box = QVBoxLayout()
        self.hint = QLabel("Press SPACE to select the highlighted option")
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setStyleSheet("color:#EEB422; font-size:16pt;")

        root.addWidget(self.context_box)
        root.addWidget(self.title)
        root.addWidget(self.source)
        root.addWidget(self.question_box)
        root.addLayout(self.box)
        root.addWidget(self.hint)

        self.buttons, self.options, self.index = [], [], 0
        self.worker = self.speaker = None
        self.history = []          # last things actually spoken (memory only)
        self.pending_question = ""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.advance)

        self.eye = None
        if BlinkSwitch and "--keyboard" not in sys.argv:
            try:
                self.eye = BlinkSwitch()
                self.eye.selected.connect(self.select_current)
                self.hint.setText("Close your eyes for about 1 second to select")
            except Exception as e:
                print("Camera input failed, using keyboard:", e)

        self.show_home()
        self.showMaximized()
        self.setFocus()

    # ---- generic scanning menu ----
    def set_options(self, title, options):
        self.title.setText(title)
        for b in self.buttons:
            b.deleteLater()
        self.buttons = []
        self.options = options
        for label, _ in options:
            b = QPushButton(label)
            b.setFocusPolicy(Qt.NoFocus)
            self.box.addWidget(b)
            self.buttons.append(b)
        self.index = 0
        self.refresh()
        if options:
            self.timer.start(SCAN_MS)
        else:
            self.timer.stop()

    def refresh(self):
        for i, b in enumerate(self.buttons):
            b.setStyleSheet(ACTIVE if i == self.index else IDLE)

    def advance(self):
        if self.options:
            self.index = (self.index + 1) % len(self.options)
            self.refresh()

    def select_current(self):
        if self.options:
            self.options[self.index][1]()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space and not event.isAutoRepeat():
            self.select_current()

    def closeEvent(self, event):
        if self.eye:
            self.eye.stop()
        event.accept()

    # ---- context sent to the model ----
    def context(self):
        parts = []
        note = self.context_box.text().strip()
        if note:
            parts.append(f"Caregiver note: {note}")
        if self.history:
            parts.append("Recent conversation, oldest first: "
                         + " ".join(self.history))
        return " ".join(parts)

    # ---- screens ----
    def show_home(self):
        self.question_box.hide()
        self.source.setText("")
        self.setFocus()
        opts = [("Someone asked me a question", self.show_question)]
        opts += [(label, lambda c=code, l=label: self.request("situation", l, c))
                 for label, code in SITUATIONS]
        if self.history:
            opts.append(("Start a new conversation", self.new_conversation))
        self.set_options("What do you want to say?", opts)

    def new_conversation(self):
        self.history = []
        self.show_home()

    def show_question(self):
        self.set_options("Someone is asking you something...",
                         [("<- Back", self.show_home)])
        self.question_box.show()
        self.question_box.setFocus()

    def ask(self):
        question = self.question_box.text().strip()
        if not question:
            return
        self.question_box.clear()
        self.question_box.hide()
        self.setFocus()
        self.request("answer", question)

    def request(self, mode, text, code=""):
        self.pending_question = text if mode == "answer" else ""
        self.set_options("Asking the AI for phrases...", [])
        self.worker = PhraseWorker(mode, text, self.context(), code)
        self.worker.done.connect(self.show_phrases)
        self.worker.start()

    def show_phrases(self, phrases, source):
        color = "#FF8C00" if "MOCK" in source else "#4A90E2"
        self.source.setStyleSheet(f"color:{color}; font-size:16pt;")
        self.source.setText(f"Phrases from: {source}")
        if not phrases:
            self.show_home()
            return
        opts = [(p, lambda p=p: self.confirm(p)) for p in phrases]
        opts.append(("<- Back", self.show_home))
        title = (f'Question: "{self.pending_question}"'
                 if self.pending_question else "Choose what to say")
        self.set_options(title, opts)

    def confirm(self, phrase):
        opts = [("SPEAK", lambda: self.speak(phrase)),
                ("CANCEL", self.show_home)]
        self.set_options(f"Say this?  \"{phrase}\"", opts)

    def speak(self, phrase):
        asked = (f'Someone asked: "{self.pending_question}". '
                 if self.pending_question else "")
        self.history.append(f'{asked}The user said: "{phrase}".')
        self.history = self.history[-4:]
        self.set_options("Speaking...", [])
        self.speaker = Speaker(phrase)
        self.speaker.finished.connect(self.show_home)
        self.speaker.start()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PhrasesWindow()
    sys.exit(app.exec_())