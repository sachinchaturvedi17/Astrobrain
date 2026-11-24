# NaradVani: from living portrait to 3D and Unreal

## What 1.2.0 is

A **2D living portrait**, with no dependencies and no server cost. One photo (`naradvani.jpg`) is drawn on a canvas.

- **Chat mode:** silent. Natural blinking (random gaps, occasional double blink) and a slow breathing sway.
- **Talk mode:** the browser's own speech voice reads replies (prefers a male en-IN / hi-IN voice). The mouth opens and closes with the text being spoken, eyebrows lift on questions and new sentences, and the head nods slightly. A mic button sends what you say to NaradVani (browser speech recognition).

Limits, stated plainly:

- Lip movement is driven by the **text**, re-synced on each word boundary the browser reports. It is a believable approximation, not audio-exact phoneme tracking.
- The voice depends on the browser and operating system. Hindi voices are not on every machine. Chrome and Edge give the best speech recognition; the audio goes to the browser vendor's service.
- It is not 3D and not Unreal. A single photo cannot turn its head or show a new expression it does not contain.
- The portrait is AI-generated and still carries the generator's invisible provenance mark (SynthID). The UI says NaradVani is an AI character.

## Calibration

All landmarks live in `CAL` at the top of `static/live.js` (eye centres and skin strips, brow patches, mouth box). A different portrait only needs new numbers. `AMLive.preview(blink, mouth, brow)` freezes a frame for tuning.

## Next steps, in order of value for money

1. **Better voice (server TTS).** Piper (MIT engine) has Hindi and Indian-English voices in `rhasspy/piper-voices`; each voice has its own dataset licence, so check before shipping. Audio from the server also gives real viseme timing instead of guessing from text.
2. **A real 3D head in the browser.** three.js with a GLB avatar that has ARKit / Oculus viseme blendshapes. The MIT-licensed `met4citizen/TalkingHead` already does lip-sync, blinking, moods and gestures for Ready Player Me / Mixamo-style avatars, and can take word timestamps from a TTS. This is the practical route to a turning head, smiles and gestures at near-zero server cost.
3. **The astrologer's shop.** A background scene (lamp, incense, shelves) behind the 3D head, as a three.js scene or a layered image. Cheap and works on phones.
4. **Unreal Engine.** Possible through Pixel Streaming, but each interactive user needs their own GPU render instance streamed over WebRTC; it does not run natively in a browser. Published figures put this at roughly $1 per hour per session on a cloud GPU. That does not fit a free, no-timer product unless sessions are short or capped. Reasonable for a kiosk or a premium experience, not as the default.

## Licence cautions

- LivePortrait: code and weights are MIT, but its default face detector (InsightFace buffalo_l) is non-commercial.
- Wav2Lip: commercial use is prohibited.
- Avatars, voices and Mixamo animations each carry their own terms. Record the source and licence of every asset in the repo.
