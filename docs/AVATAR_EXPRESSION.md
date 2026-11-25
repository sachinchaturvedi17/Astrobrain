# Resting expression (friendly smile) - updated 2026-11-23 (r7/r8)

Set as shape-key values on every mesh with ARKit keys (AvatarHead, AvatarEyelashes, eye_wet) in
assets_src/private/metaperson/naradvani_mp_r7.blend. The shape keys themselves are unchanged.

| key | value |
|---|---|
| mouthSmileLeft / Right | 0.75 / 0.72 |
| cheekSquintLeft / Right | 0.45 / 0.43 |
| eyeSquintLeft / Right | 0.28 / 0.26 |
| mouthUpperUpLeft / Right | 0.14 |
| mouthLowerDownLeft / Right | 0.10 |
| jawOpen | 0.07 |
| browInnerUp | 0.06 |
| browOuterUpLeft / Right | 0.05 / 0.04 |
| noseSneerLeft / Right | 0.04 |

Before export decide where the smile lives: bake these as default weights, OR zero them in Blender and let the
page driver apply a (stronger) smile. The page driver already adds 0.14 to 0.22; do not let both stack.

# Free realism layers added (no downloads, all procedural, 2026-11-23)
- textures/mp_head_albedo_r8.png and mp_head_normal_r8.png: stubble, cheek spots, under-eye shading,
  crow's feet, forehead lines, smile lines, extra pore dips. Built from r7 + r8_layers.npz (git-ignored, private).
- Hair: hair_layers and hair_thick given a spiral curl toward the ends (25% strength on the front half).
  Backups kept inside the .blend: hair_layers_backup_r7, hair_layers_backup_r8, hair_thick_backup_r8.

## Preset: warm_smile_teeth (from the kurta reference model)

Broad, warm smile with the upper teeth visible and squinting (smiling) eyes. Stored in the blend as text block `expr_presets.json`.

| Shape key | Value |
|---|---|
| mouthSmileLeft / Right | 0.88 |
| cheekSquintLeft / Right | 0.58 |
| eyeSquintLeft / Right | 0.40 |
| mouthUpperUpLeft / Right | 0.34 |
| mouthLowerDownLeft / Right | 0.16 |
| mouthDimpleLeft / Right | 0.20 |
| jawOpen | 0.12 |
| browInnerUp | 0.08 |
| browOuterUpLeft / Right | 0.08 |
| noseSneerLeft / Right | 0.08 |

Use for greetings and happy moments. Caveat: the page driver (`avatar3d.js`) adds a resting smile of 0.14-0.22, so when this preset is played, clamp the sum to 1 or fade the resting smile out first.
