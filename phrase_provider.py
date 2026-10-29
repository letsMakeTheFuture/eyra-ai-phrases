from abc import ABC, abstractmethod


class PhraseProvider(ABC):
    name = "base"

    @abstractmethod
    def suggest(self, situation: str, context: str = "") -> list[str]:
        """Up to 3 short phrases for a situation the user chose."""

    @abstractmethod
    def answer(self, question: str, context: str = "") -> list[str]:
        """Up to 3 short replies to a question someone asked the user."""


class MockProvider(PhraseProvider):
    name = "MOCK (fixed phrases, not AI)"
    PHRASES = {
        "HELP": ["Could you please help me?",
                 "I need assistance with something.",
                 "Please come here, I need help."],
        "PAIN": ["I am in pain.", "I am uncomfortable.",
                 "Please call a doctor."],
        "NEED": ["I need some water.", "I need to rest.",
                 "I need something, please wait."],
    }

    def suggest(self, situation, context=""):
        return self.PHRASES.get(situation.upper(), [])

    def answer(self, question, context=""):
        return ["Yes.", "No.", "I am not sure."]