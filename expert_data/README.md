# Expert case library: where real astrologers' advice goes

NaradVani answers from your chart first. This folder is where **experienced astrologers' real advice** is kept, so that when a user brings a problem the assistant has seen before, it can add "what a practising astrologer would say".

This is retrieval, not model training: the advice is stored, searched and shown with attribution. Nothing is learned silently.

## How to add cases
1. Put `.jsonl` files (one case per line) in `expert_data/cases/`, **or** fill a spreadsheet with the columns below and run
   `python3 tools/expert_check.py --import yourfile.csv`.
2. Run `python3 tools/expert_check.py` to see which cases pass. Errors keep a case out; notes are suggestions.
3. Restart the server.

You can also just send the material (voice-note transcripts, WhatsApp text, notes, a sheet) and ask Claude to turn it into cases: it will anonymise, split into one problem per case, and run the same check.

## What one good case looks like
| field | meaning |
|---|---|
| `id` | unique, e.g. `marriage_delay_mars_003` |
| `lang` | `en`, `hg` (Hinglish) or `hi` |
| `topic` | career, wealth, marriage, education, children, health, family, foreign, property, dasha, remedy, general, manglik, kaalsarp, transit, sade_sati |
| `problem` | the person's problem in their own words, anonymised |
| `situation` | optional: what the astrologer looks for in the chart |
| `advice` | what the astrologer says: reading, first questions, practical steps, reassurance |
| `remedies` | optional: simple, low-cost practices |
| `cautions` | optional: what to avoid |
| `expert` | who gave it (a name, or "anonymous") |
| `consent` | must be `true`: the astrologer agreed to it being used |

Write the way the astrologer would actually talk to a worried person. Specific beats generic: what do they check, what do they ask, what do they tell the person to do this month.

## What is rejected automatically
Phone numbers or emails; predictions of death; guaranteed outcomes ("100%", "pakka hoga"); curses or fear; fees or booking a puja; medical cures or "stop your medicine"; investment instructions. Gemstone mentions and names get a note.

## Privacy
Real client stories must have names, places, dates of birth and contact details removed. `expert_data/cases/` is git-ignored by default so private data is not pushed to GitHub; remove that line from `.gitignore` only if the repository is private and you want the data versioned.
