# NaradVani resting expression

A calm, kind resting face (relaxed mouth with a slight smile, softened brows, a hint of warmth around
the eyes), defined only as a mix of existing ARKit shape keys. The shape keys themselves are unchanged.

## Values (influence 0..1, applied on top of the neutral base)

| Shape key          | Value | Purpose                                   |
| ---                | ---   | ---                                       |
| mouthSmileLeft     | 0.28  | slight warm smile (left a touch stronger) |
| mouthSmileRight    | 0.26  | slight warm smile                         |
| cheekSquintLeft    | 0.22  | cheeks lift with the smile                |
| cheekSquintRight   | 0.20  | cheeks lift with the smile                |
| eyeSquintLeft      | 0.18  | warmth in the eyes                        |
| eyeSquintRight     | 0.18  | warmth in the eyes                        |
| browInnerUp        | 0.12  | softened, open brows                      |
| browOuterUpLeft    | 0.04  | relaxes the brow line                     |
| browOuterUpRight   | 0.04  | relaxes the brow line                     |
| mouthDimpleLeft    | 0.10  | softens the mouth corners                 |
| mouthDimpleRight   | 0.10  | softens the mouth corners                 |
| jawOpen            | 0.03  | lips just relaxed, not pressed            |
| mouthShrugUpper    | 0.05  | relaxed upper lip                         |

All other shape keys rest at 0. The left/right differences are intentional (slight natural asymmetry).

## How to apply

- Use these as the idle/rest target. Blink, gaze, lip-sync and other expressions are added on top.
- While speaking, halve mouthSmileLeft/Right (0.14 / 0.13) so visemes read clearly; restore when silent.
- Visemes and jawOpen take priority over the resting mouth values (use the larger value per key).

## Verified (Blender render, private MetaPerson build)

Rest mix plus smile, jawOpen 0.45, full blink, viseme_aa, viseme_O, viseme_PP and viseme_FF all
deform cleanly with no interpenetration; PP closes the lips fully. Review images:
`assets_src/private/review/r7_*`.

Not yet wired into `avatar3d.js` (no page or export changes in this round).
