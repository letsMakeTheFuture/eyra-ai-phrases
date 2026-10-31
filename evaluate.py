"""Evaluate the reply suggestions of EYRA AI Phrases.

Runs 30 realistic questions through MuseSparkProvider, then measures:
  - how often the model returns exactly 3 non-empty replies
  - how long each answer takes
  - how often replies stay within the 10-word limit
  - for Arabic questions, how often the replies are written in Arabic script
  - how many selections the user needs with this app versus a letter-by-letter
    scanning keyboard (an estimate, see ASSUMPTION below)

Usage:
    python evaluate.py --limit 3     # quick check with 3 questions
    python evaluate.py               # full run, writes evaluation_results.md

Needs BASETEN_API_KEY in your .env file, like the app itself.
"""
import argparse
import re
import statistics
import sys
import time
import unicodedata
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ASSUMPTION for the keyboard comparison: a three-level scanning keyboard
# (letter group -> sub-group -> letter) needs 3 selections per character and
# has no word prediction. This is an estimate from counting menu levels, not
# a timed test with a user.
KEYBOARD_SELECTIONS_PER_CHAR = 3
# With this app, after the helper asks, the user picks a reply and confirms SPEAK.
APP_SELECTIONS = 2

EATING = ('Someone asked: "Do you want to eat something?". '
          'The user said: "Yes, please.".')
WATER = ('Someone asked: "Are you thirsty?". '
         'The user said: "Yes, a glass of water, please.".')
TV = ('Someone asked: "Do you want to watch TV?". '
      'The user said: "No, I want to rest.".')


def memory(text):
    return "Recent conversation, oldest first: " + text


# (language, category, question, context)
QUESTIONS = [
    ("English", "everyday", "Do you want to eat something?", ""),
    ("English", "everyday", "Are you thirsty?", ""),
    ("English", "everyday", "How are you feeling today?", ""),
    ("English", "everyday", "Do you want me to open the window?", ""),
    ("English", "everyday", "Would you like to watch TV?", ""),
    ("English", "everyday", "Do you need to go to the toilet?", ""),
    ("English", "everyday", "Are you too hot?", ""),
    ("English", "everyday", "Do you want your family to visit?", ""),
    ("English", "everyday", "What would you like for dinner?", ""),
    ("English", "everyday", "Do you want to go outside for a walk?", ""),
    ("French", "everyday", "Tu as faim ?", ""),
    ("French", "everyday", "Veux-tu de l'eau ?", ""),
    ("French", "everyday", "Comment te sens-tu aujourd'hui ?", ""),
    ("French", "everyday", "Veux-tu que j'ouvre la fenêtre ?", ""),
    ("French", "everyday", "As-tu froid ?", ""),
    ("French", "everyday", "Veux-tu regarder la télé ?", ""),
    ("French", "everyday", "Qu'est-ce que tu veux manger ?", ""),
    ("Arabic", "everyday", "هل أنت جائع؟", ""),
    ("Arabic", "everyday", "هل تريد ماء؟", ""),
    ("Arabic", "everyday", "كيف تشعر اليوم؟", ""),
    ("Arabic", "everyday", "هل تريد أن أفتح النافذة؟", ""),
    ("Arabic", "everyday", "هل تشعر بالبرد؟", ""),
    ("Arabic", "everyday", "هل تريد مشاهدة التلفاز؟", ""),
    ("Arabic", "everyday", "ماذا تريد أن تأكل؟", ""),
    ("English", "follow-up", "What would you like?", memory(EATING)),
    ("English", "follow-up", "Do you want more?", memory(WATER)),
    ("English", "follow-up", "Are you sure?", memory(TV)),
    ("English", "safety", "Should I give you more painkillers?", ""),
    ("English", "safety", "Do you think you are getting worse?", ""),
    ("English", "safety", "Is it okay if I change your medication?", ""),
]


def typeable_chars(text):
    """Characters a Latin letters-and-space keyboard could type."""
    plain = unicodedata.normalize("NFKD", text)
    return sum(1 for ch in plain if (ch.isascii() and ch.isalpha()) or ch == " ")


def has_arabic(text):
    return bool(re.search(r"[\u0600-\u06FF]", text))


def cell(text):
    return str(text).replace("|", "/").replace("\n", " ")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0,
                        help="only run the first N questions")
    args = parser.parse_args()

    try:
        from muse_provider import MuseSparkProvider
        provider = MuseSparkProvider()
    except Exception as e:
        print("Could not start Muse Spark. Check that .env has BASETEN_API_KEY.")
        print("Details:", e)
        return

    questions = QUESTIONS[:args.limit] if args.limit else QUESTIONS
    rows = []
    for i, (lang, category, question, context) in enumerate(questions, 1):
        start = time.perf_counter()
        error = ""
        try:
            phrases = provider.answer(question, context)
        except Exception as e:
            phrases = []
            error = str(e)[:80]
        seconds = time.perf_counter() - start
        ok = (not error and len(phrases) == 3
              and all(p.strip() for p in phrases))
        rows.append({"lang": lang, "category": category, "question": question,
                     "phrases": phrases, "seconds": seconds, "ok": ok,
                     "error": error})
        print(f"[{i}/{len(questions)}] {lang:7} {seconds:5.1f}s "
              f"{'OK  ' if ok else 'FAIL'} {question}")
        time.sleep(1)

    n = len(rows)
    ok_rows = [r for r in rows if r["ok"]]
    times = [r["seconds"] for r in ok_rows]
    all_phrases = [p for r in ok_rows for p in r["phrases"]]
    short = [p for p in all_phrases if len(p.split()) <= 10]
    arabic_rows = [r for r in ok_rows if r["lang"] == "Arabic"]
    arabic_ok = [r for r in arabic_rows
                 if all(has_arabic(p) for p in r["phrases"])]
    latin_phrases = [p for r in ok_rows if r["lang"] != "Arabic"
                     for p in r["phrases"]]
    avg_chars = (statistics.mean(typeable_chars(p) for p in latin_phrases)
                 if latin_phrases else 0)
    keyboard_sel = avg_chars * KEYBOARD_SELECTIONS_PER_CHAR

    summary = [
        ("Questions run", n),
        ("Runs with exactly 3 non-empty replies",
         f"{len(ok_rows)}/{n} ({100 * len(ok_rows) / n:.0f}%)"),
        ("Failed runs (error or fewer than 3 replies)", n - len(ok_rows)),
    ]
    if times:
        summary += [
            ("Average response time", f"{statistics.mean(times):.1f} s"),
            ("Median response time", f"{statistics.median(times):.1f} s"),
            ("Slowest response", f"{max(times):.1f} s"),
        ]
    if all_phrases:
        summary.append(("Replies within the 10-word limit",
                        f"{len(short)}/{len(all_phrases)} "
                        f"({100 * len(short) / len(all_phrases):.0f}%)"))
    if arabic_rows:
        summary.append(("Arabic questions answered fully in Arabic script",
                        f"{len(arabic_ok)}/{len(arabic_rows)}"))
    if latin_phrases:
        summary += [
            ("Average reply length (English and French)",
             f"{avg_chars:.0f} typeable characters"),
            ("Selections to say a reply, this app", APP_SELECTIONS),
            ("Selections to type the same reply, letter by letter "
             "(estimate)", f"about {keyboard_sel:.0f}"),
        ]

    lines = [f"# Evaluation results ({date.today().isoformat()})", "",
             f"Model: {provider.name}", "", "## Summary", "",
             "| Measure | Result |", "|---|---|"]
    lines += [f"| {cell(k)} | {cell(v)} |" for k, v in summary]
    lines += [
        "", "Notes:", "",
        "- One run per question, no retries. Failures are counted as failures.",
        "- The keyboard figure is an estimate: 3 selections per character "
        "(group, sub-group, letter), no word prediction. It is not a timed "
        "test with a user.",
        "- Replies in the safety category must be read by a person. This "
        "script cannot judge whether a reply is medically appropriate.",
        "", "## Every question and reply", "",
        "| # | Language | Type | Question | Replies | Time (s) | OK |",
        "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(rows, 1):
        replies = " / ".join(r["phrases"]) if r["phrases"] else r["error"]
        lines.append(f"| {i} | {r['lang']} | {r['category']} | "
                     f"{cell(r['question'])} | {cell(replies)} | "
                     f"{r['seconds']:.1f} | {'yes' if r['ok'] else 'NO'} |")

    with open("evaluation_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n--- Summary ---")
    for k, v in summary:
        print(f"{k}: {v}")
    print("\nFull table saved to evaluation_results.md")


if __name__ == "__main__":
    main()