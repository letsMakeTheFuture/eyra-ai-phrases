import os
from dotenv import load_dotenv
from openai import OpenAI
from phrase_provider import PhraseProvider

load_dotenv()


class MuseSparkProvider(PhraseProvider):
    name = "Muse Spark Open (Meta) via Baseten"

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("BASETEN_API_KEY"),
            base_url="https://inference.baseten.co/v1",
            timeout=20,
        )

    def _ask(self, prompt):
        response = self.client.chat.completions.create(
            model="meta-models/muse-spark-open",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7,
        )
        text = response.choices[0].message.content or ""
        lines = [l.lstrip(" -*\"'0123456789.").rstrip(" \"'")
                 for l in text.splitlines()]
        phrases = [l for l in lines if l][:3]
        if not phrases:
            raise RuntimeError("Model returned an empty reply")
        return phrases

    def _context(self, context):
                return f" Extra context: {context}." if context else ""

    def suggest(self, situation, context=""):
        return self._ask(
            "You help a person who cannot speak communicate."
            f" Situation they chose: {situation}.{self._context(context)}"
            " Write exactly 3 short, polite, first-person phrases"
            " (max 10 words each), one per line, no numbering, no quotes."
        )

    def answer(self, question, context=""):
        return self._ask(
            "You help a person who cannot speak communicate."
            f" Someone asked them: \"{question}\".{self._context(context)}"
            " Write exactly 3 different short first-person replies they might"
            " want to give (max 10 words each), such as a yes, a no, and an"
            " uncertain or other reply when it makes sense."
            " One per line, no numbering, no quotes."
        )