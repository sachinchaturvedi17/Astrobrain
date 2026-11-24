# Feedback after Round 2 - user review, 2026-11-23

Round 2 face/skin/tilak/hair-edge: accepted so far. Open item: the MALA still needs rework.
View these references in assets_src/private/review/:
- ref_rudraksha_mala.png (man's neck, two parallel rows)
- ref_mala_closeup_beads.png, ref_mala_redthread.jpg (real bead surface, red thread)
- ref_mala_on_neck_single.png (how a strand sits on the neck/collarbone)

## Mala layout is wrong
In the current render the two strands interleave and tangle at the bottom centre and
climb sideways into the hair. Required:
- TWO separate smooth U-shaped loops, one inside the other (concentric, parallel curves).
- Each loop is ONE continuous chain of single beads, one bead wide, end to end.
- NO beads between or bridging the two loops; no overlap, crossing or clumping.
  A clear, even gap between the loops (about half a bead) or loops just touching side by side.
- Upper loop sits at the base of the neck and wraps round behind it under the hair
  (hide the back part cleanly); lower loop hangs on the chest, symmetrical left and right.
- Both follow the body surface with a small offset (shrinkwrap), nothing floating.
- Beads ordered along a single curve per loop (generate from a curve, then place beads
  on it), not scattered or doubled up.

## Bead SIZE: reduce
Beads are too big. Reduce by about 35 to 40 percent: about 1.2 cm at the sides up to about
1.4 cm at bottom centre (was 1.8 to 2.2 cm). More beads per loop will be needed (about 50 to 60
upper, 56 to 66 lower). Keep them touching.

## Bead look
Currently glossy like basketballs with a single equator groove. Real rudraksha (see refs):
matte or satin, warm orange-brown with darker brown in crevices, bumpy thorny surface with
irregular wrinkles, a few faint mukhi lines, NOT one clean groove. Lower the specular a lot.
Optional: tiny red thread visible between beads.

## Process
Fix the mala only, render front view and a neck close-up into assets_src/private/review/,
stop for approval. Then Round 3 (eyes). No export, commit or push without approval.
