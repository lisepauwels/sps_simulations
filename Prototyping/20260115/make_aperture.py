import xtrack as xt
import numpy as np

line_layoutdb = xt.Line.from_json('../../injection_lines/sps_with_aperture_inj_q20_beam_sagitta4.json')
line_layoutdb['qph_setvalue'] = 0.5
line_layoutdb['qpv_setvalue'] = 0.5

def get_aper(ee):
    if isinstance(ee, xt.LimitPolygon):
        raise NotImplementedError
    max_x = 100
    min_x = -100
    max_y = 100
    min_y = -100
    if hasattr(ee, 'max_x'):
        max_x = ee.max_x
    if hasattr(ee, 'min_x'):
        min_x = ee.min_x
    if hasattr(ee, 'a_squ'):
        max_x = min(np.sqrt(ee.a_squ), max_x)
        min_x = max(-np.sqrt(ee.a_squ), min_x)
    if hasattr(ee, 'max_y'):
        max_y = ee.max_y
    if hasattr(ee, 'min_y'):
        min_y = ee.min_y
    if hasattr(ee, 'b_squ'):
        max_y = min(np.sqrt(ee.b_squ), max_y)
        min_y = max(-np.sqrt(ee.b_squ), min_y)
    if hasattr(ee, '_sin_rot_s') and -2 < ee._sin_rot_s < 2:
        old_max_x = max_x
        max_x = ee._cos_rot_s * max_x + ee._sin_rot_s * max_y
        max_y = -ee._sin_rot_s * old_max_x + ee._cos_rot_s * max_y
    if hasattr(ee, '_shift_x'):
        max_x += ee._shift_x
        min_x += ee._shift_x
    if hasattr(ee, '_shift_y'):
        max_y += ee._shift_y
        min_y += ee._shift_y
    return max_x, min_x, max_y, min_y

tt = line_layoutdb.get_table()
tt_aper = tt.rows[[ttt.startswith('Limit') for ttt in tt.element_type]].cols['name s']
tt_aper.aper_max_x, tt_aper.aper_min_x, tt_aper.aper_max_y, tt_aper.aper_min_y = \
    np.array([list(get_aper(line_layoutdb[nn]))  for nn in tt_aper.name]).T
