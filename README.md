# EYRA AI Phrases

An AI reply assistant for people who can only move their eyes, such as
someone with quadriplegia. Someone asks a question, Meta's Muse Spark Open
suggests short replies, the user picks one with a long blink, confirms,
and the app speaks it. Nothing is ever spoken without the user's confirmation.

## What is new (built Oct 26 - Nov 4, 2026, solo, Indie track)

Everything in this repository was written during the hackathon:

- Reply suggestions from Muse Spark Open (served through Baseten)
- Reply mode: a helper types the question, or taps a ready-made one, and the
  model suggests 3 replies
- Quick questions screen (hungry, thirsty, in pain, toilet, too hot or cold)
  so the helper does not have to type
- Situation buttons (help / pain / need) that work with no typing at all
- Short-term conversation memory (last 4 spoken exchanges)
- Optional helper note (where we are, who is here)
- Scanning screen with blink selection (hold eyes closed for under a second)
- Blink detection with plain OpenCV image processing and no pretrained model
  (see "Blink switch" below)
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
  writes every reply suggestion at runtime. It is the only AI model the
  application calls.
- **Blink detection** uses plain OpenCV and NumPy image processing on the
  camera image. It does not use any pretrained model, face detector,
  Haar cascade or neural network. The organizers confirmed on the hackathon
  Discord that plain OpenCV without a pretrained model is allowed.
- **Windows system voices** through `pyttsx3`: read the chosen reply aloud,
  locally. This is not an AI model call.
- No other cloud AI service is used.

### Removed code (visible in git history only)

Earlier commits during the event contained a Google speech-to-text feature
and a MediaPipe-based blink detector. Both were removed before submission
because the rules require every model called at runtime to be a Meta model.
Neither is part of the current code.

## Blink switch

The camera does not use face tracking. At start-up the helper draws a box
around one eye. The app then asks the user to keep the eye open and then
closed (a beep marks each step), measures the box with five simple image
measures, and automatically keeps the one that separates open from closed
best. Holding the eye closed for a short moment selects the highlighted
option, and the eye must reopen before the next selection.

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
2. `pip install -r requirements.txt` (use `opencv-python`, not the headless
   version, because the setup window needs it)
3. Create a `.env` file containing: `BASETEN_API_KEY=your_key_here`
4. Run:
   - `python phrases_screen.py` (blink input, needs a webcam; follow the
     setup beeps)
   - `python phrases_screen.py --keyboard` (SPACE key instead of blink;
     any single switch can drive it)

## Measured results

I tested the reply suggestions with 30 questions: 10 English, 7 French,
7 Arabic, 3 follow-ups that use the conversation memory, and 3 about pain
and medication. One run per question, no retries. Run `python evaluate.py`
to repeat the test. Every question and reply is listed in
`evaluation_results.md`.

| Measure | Result |
|---|---|
| Runs with exactly 3 non-empty replies | 30/30 (100%) |
| Average response time | 3.2 s |
| Median response time | 2.8 s |
| Slowest response | 10.8 s |
| Replies within the 10-word limit | 90/90 (100%) |
| Arabic questions answered fully in Arabic script | 7/7 |
| Selections to say a reply with this app | 2 (pick a reply, confirm SPEAK) |
| Selections to type the same reply letter by letter (estimate) | about 79 |

Notes:

- Timings were measured once, from Algeria through Baseten, so they include
  the network. Results will vary.
- The keyboard figure is an estimate: 3 selections per character (letter
  group, sub-group, letter) and no word prediction. It is not a timed test
  with a user.
- This test measures the model's replies only. It does not test the blink
  switch, and it was not done with real users.
- The replies to the 3 pain and medication questions were read by hand. They
  only offer the user's own yes, no or unsure answers, and none gives medical
  advice. The user still has to choose and confirm any reply before it is
  spoken.

## Known limitations

- The question is typed or tapped by a helper. Voice input is planned future
  work (Meta's Muse Voice Transcribe is only available through Meta's own
  API, which I could not access because of billing restrictions).
- Blink detection without a pretrained model is less robust and less
  comfortable than face tracking. It needs steady light, a fixed camera
  and head position after setup, and a new setup at every start. The hold
  time can be changed with `hold_seconds` in `eye_switch.py`.
- Speech depends on installed Windows voices. French needs the French voice
  pack. Arabic replies are shown on screen, but Arabic speech did not work
  with `pyttsx3` on my machine.
- Arabic replies are written in standard Arabic, not in Algerian dialect.
- Not yet tested with real users. Suggestions can be wrong, which is why
  the user always confirms first.