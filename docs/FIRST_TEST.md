# First test with a real person (v0.6, AstroMuni)

Goal of this round: find out whether a real user understands the answers, trusts the tone, and finds the Hinglish
natural. It is **not** a measurement of astrological accuracy (see "What this test cannot tell you").

## 1. Run it (5 minutes)

```bash
cd astromuni
bash start.sh                     # or double-click start.command on a Mac; opens http://127.0.0.1:8000
```
Feedback goes to `./aipandit-feedback/feedback.jsonl`; **requests to talk to a real pandit** go to
`./aipandit-feedback/pandit_requests.jsonl` (phone number, birth details, optional palm photos in `pandit_requests/`).
Nothing is forwarded automatically: someone has to read that file and call the person back. Treat it as personal data:
keep it private and delete it when the test is over. `python tools/feedback_summary.py` summarises the feedback file only.

- Same Wi-Fi, phone as the tester's device: `aipandit-web --host 0.0.0.0`, then open `http://<your-computer-ip>:8000`
  on the phone. There is **no login and no HTTPS**: use only on a network you trust, and stop the server afterwards.
  Do not put it on the public internet as is.
- Optional model-written wording (nicer Hindi, more natural phrasing):
  `pip install -e '.[llm]' && export ANTHROPIC_API_KEY=... && aipandit-web --llm`. This path has **never been run
  against the live API**; run `python tools/live_llm_check.py --show` first and read the Hindi yourself.
  Without `--llm` everything works: English and Hinglish answers come from reviewed-by-code rule wording; a question in
  Devanagari gets the English answer plus a Hindi note.

## 2. Sit with the tester (do not explain the screen)

1. Ask them to fill the three steps (name, birth details, both palm photos). Time how long it takes and where they
   hesitate: the palm step is the most likely drop-off, so note who skips or resists it.
2. On the "what do you want?" screen say nothing. Note which of the four tools they open first. Then, in AstroMuni,
   say only: "Ask whatever you would ask a pandit." Let them type in their own language. Note the questions they try
   that the Pandit cannot answer (children, education, health, "when will I..."): this is your backlog.
3. After 3-4 answers: ask them to tap the thumbs on each answer and to use **Feedback dein** at the end.
4. Ask afterwards (in this order, do not lead):
   - What did you think the "Kundli / Numerology / Both lenses" labels meant?
   - Which answer felt most about *you*? Which felt generic?
   - Was anything scary, wrong, or something you would not repeat to a family member?
   - Was the Hinglish natural? Which sentence sounded odd?
   - Would you have wanted a date ("when")? How did you feel when the Pandit declined?
   - Would you pay, return, or send this to someone? Why / why not?

## 3. What to watch for

| Signal | Why it matters |
|---|---|
| Thumbs-down on answers containing "provisional" readings | Rule wording needs the astrologer review |
| Tester skips the note lines | Check that "tendencies, not predictions" is still understood |
| Tester asks the same thing in Devanagari | Needs `--llm` or Hindi rule wording |
| Name number differs from what they use | Spelling variants change the number; expected, but note it |
| Bridge note ("Both lenses single out Venus...") | Do they read it as proof? It is a coincidence note, not confirmation |
| Answers over ~6 readings feel long | Cap is 6 readings + numbers; shorten if people stop reading |

Read the results: `python tools/feedback_summary.py` (thumbs by language/lens, rules behind thumbs-down, all comments).

## 4. Privacy and consent

- Birth details and the name live in server memory for the session only; they are **never** written to disk or logs.
- `feedback.jsonl` stores: rating, comment, rule ids, composer, language, lenses, a hashed tester id. The **question text
  is saved only if the tester ticked the consent box** on the form.
- If the tester is under 18, a parent/guardian must be present and choose "A child" on the form. The Pandit then shows no
  marriage content and no cautionary readings. Do not collect anything from minors beyond what is above.
- Tell the tester what is saved, and delete `aipandit-feedback/` when the test is over if they ask.

## 5. What this test cannot tell you

- **Accuracy.** Nobody has validated that kundli or numerology readings predict anything. A tester saying "this is so
  true" is mostly the Barnum effect (general statements feel personal). Use thumbs-down and "generic" comments, not
  praise, as the signal. A fair accuracy test needs blinded charts (readings for a chart that is not theirs, compared with
  theirs) and astrologer review.
- **Hindi quality.** Hinglish/Hindi fixed sentences and Hinglish rule wording were written by an AI and have not been read
  by a native speaker or astrologer. Collect the sentences testers call odd and fix them.
- **Numerology.** No classical text; scheme choices (Chaldean names, Indian number-planet map) are one of several. Name
  number changes with spelling.
- **Load/security.** Development server, in-memory sessions, no auth.

## v0.6 additions to watch for

- *Palm photos.* Do testers expect AstroMuni to read the palms? It does not; the screen says so. Note any disappointment: it
  decides whether to ask for photos at all before there is a palm feature.
- *Thinking pause.* Is 2-3 s pleasant or irritating on the third question? (It is the same length every time.)
- *Silhouette.* Does "a person sitting in front of me" help, or does it make people think it is a human? The label says AI.
- *Horoscope.* Do testers take it for a daily forecast? It is not one.
- *Real pandit.* If you offer this to testers, you must actually call them back. Do not leave requests unanswered.
