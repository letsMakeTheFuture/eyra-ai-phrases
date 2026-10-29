from abc import ABC, abstractmethod


class PhraseProvider(ABC):
    name = "base"

    @abstractmethod
    def suggest(self, situation: str) -> list[str]:
        """Return up to 3 short phrases for a situation."""


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
        "ANSWER": ["Yes.", "No.", "I am not sure yet."],
    }

    def suggest(self, situation):
        return self.PHRASES.get(situation.upper(), [])