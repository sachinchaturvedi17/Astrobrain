# NaradVani avatar build step, run inside Blender 5.3 + MPFB 2.0.18 (exported from the working .blend).

import os
from bl_ext.blender_org.mpfb.services import TargetService
def _key(obj, tname):
    full = TargetService.target_full_path(tname)
    sk = TargetService.filename_to_shapekey_name(full)
    return full, sk
def set_t(obj, cat, value, side=None):
    """cat like 'nose-scale-horiz-decr-incr'; value -1..1; side 'l','r' or None (both if LR)."""
    parts = cat.split('-'); neg, pos = parts[-2], parts[-1]; stem = '-'.join(parts[:-2])
    sides = [side] if side else ([None] if not obj.get('_lr_'+cat) else [])
    names = []
    for s in (['l','r'] if side == 'both' else [side]):
        pre = (s + '-') if s else ''
        for word, val in ((neg, max(0.0,-value)), (pos, max(0.0,value))):
            tname = pre + stem + '-' + word
            full, sk = _key(obj, tname)
            if not os.path.exists(full):
                raise FileNotFoundError(full)
            if obj.data.shape_keys and sk in obj.data.shape_keys.key_blocks:
                obj.data.shape_keys.key_blocks[sk].value = val
            elif val > 0:
                TargetService.load_target(obj, full, weight=val, name=sk)
            names.append((sk, round(val,3)))
    return names
