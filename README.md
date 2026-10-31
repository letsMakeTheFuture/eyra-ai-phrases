# EYRA AI Phrases

An AI reply assistant for people who can only move their eyes, such as
someone with quadriplegia. Someone asks a question, Meta's Muse Spark Open
suggests short replies, the user picks one with a long blink, confirms,
and the app speaks it. Nothing is ever spoken without the user's confirmation.

## What is new (built Oct 26 - Nov 4, 2026, solo, Indie track)

Everything in this repository was written during the hackathon:

- Reply suggestions from Muse Spark Open (served through Baseten)
- Reply mode: a helper types the question, the model suggests 3 replies
- Situation buttons (help / pain / need) that work with no typing at all
- Short-term conversation memory (last 4 spoken exchanges)
- Optional helper note (where we are, who is here)
- Scanning screen with blink selection (hold eyes closed ~1 second)
- Confirm screen (SPEAK / CANCEL) before anything is spoken
- Replies in the language of the question (tested with English, French, Arabic)
- Labeled fallback: if the AI cannot be reached, fixed phrases are shown
  in orange as MOCK, never presented as AI output

## What existed before

EYRA, my earlier eye-control project (gaze navigation, spelling keyboard,
wheelchair control, SOS alerts), built before the event with teammates.
It is a separate repository. No EYRA code is included here and none is
needed to run this project.

## Models and external services (full disclosure)

- **Meta Muse Spark Open** (`meta-models/muse-spark-open`) through Baseten:
  writes every reply suggestion at runtime.
- **MediaPipe Face Landmarker** (Google): detects eye closure only, to act
  as a blink switch. It runs locally. The model file is downloaded once on
  first run. `--keyboard` mode runs without it.
- **Windows system voices** through `pyttsx3`: read the chosen reply aloud,
  locally. This is not an AI model call.
- No other cloud AI service is used.

## Privacy

- The question, the helper note and the last 4 spoken exchanges are sent to
  Muse Spark through Baseten. Do not type sensitive personal details.
- Conversation memory lives only in the running program. Nothing is stored
  on disk.
- The camera is used only to detect eye closure. No images are saved or sent.
- The model is instructed never to give medical advice. It writes phrases
  for the user to say, which the user chooses and confirms.

## Install and run

1. Python 3.12 is recommended.
2. `pip install -r requirements.txt`
3. Create a `.env` file containing: `BASETEN_API_KEY=your_key_here`
4. Run:
   - `python phrases_screen.py` (blink input, needs a webcam)
   - `python phrases_screen.py --keyboard` (SPACE key instead of blink)

## Known limitations

- The question is typed by a helper. Voice input is planned future work
  (Meta's Muse Voice Transcribe is only available through Meta's own API,
  which I could not access because of billing restrictions).
- Speech depends on installed Windows voices. French needs the French voice
  pack. Arabic replies are shown on screen, but Arabic speech did not work
  with `pyttsx3` on my machine.
- Blink timing may need adjusting per user (`hold_seconds` and
  `closed_threshold` in `eye_switch.py`).
- Not yet tested with real users. Suggestions can be wrong, which is why
  the user always confirms first.
- The MediaPipe question is unresolved: the organizers have not ruled on
  whether non-generative models count under the "Meta models only" rule.
  It is disclosed here, and the project also runs in `--keyboard` mode.
