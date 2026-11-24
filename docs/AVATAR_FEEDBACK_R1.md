# Feedback after Round 1 (hair) - user review, 2026-11-23

Round 1 hair APPROVED with the fixes below. Work in naradvani_mp.blend (private).
Reference for the mala: assets_src/private/review/ref_rudraksha_mala.png (view it).

## A. Grain instead of shadow (hair edges, cheeks, neck, shoulders)
Orange/brown speckle where thin hair meets skin looks like noise, not soft shadow.
- Use clean alpha-clip (MASK) with an anti-aliased threshold, not dithered noise; check it
  the way the web GLB will draw it.
- Darken hair-card edge colour so nothing orange shows through.
- Add real soft contact shadow: bake ambient occlusion into the skin and shawl textures
  under the hair, behind the ears, neck/jaw, collar and under the mala (no runtime cost).

## B. Rudraksha mala - rework (see reference image)
Current: small beads, spaced apart, one strand climbs behind the neck with floating beads
beside the hair, strands bunch in the middle. Target (like the reference):
- 2 strands, beads TOUCHING each other, no thread gaps.
- Strand 1 sits at the base of the neck on the collarbone line; strand 2 hangs lower,
  both draping over the chest following the body surface (project/shrinkwrap onto skin,
  small offset), symmetrical, no beads floating in the hair or through the body.
- Bigger beads (about 1.8 to 2.2 cm), slightly larger toward the bottom centre.
- Real rudraksha surface: deep irregular crevices (mukhi lines) with dark recesses,
  red-brown, matte-satin. Use a bump/normal map on a low-poly bead (instances ok), not
  heavy geometry. Keep the 8 MB budget.
- Soft contact shadow of beads on skin (baked AO).

## C. Skin tone
Face and neck are too fair. Shift slightly warmer and deeper toward a wheatish / light-brown
Indian skin tone (subtle, not tan, no orange cast). Match face, neck AND chest; remove the
visible horizontal seam and colour step across the collar/chest (head vs grafted torso).
Add fine skin detail (pores, slight tonal variation).

## D. Tilak
Make bolder and cleaner: clear Vaishnava U shape per naradvani.jpg.

## Process
Then continue Round 2 (face and skin, man of about 40). Render side-by-side with
naradvani.jpg into assets_src/private/review/, show close-ups of neck, mala and hair edge,
and stop for approval. No export, commit or push without approval.
