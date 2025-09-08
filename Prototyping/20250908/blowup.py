import numpy as np
import matplotlib.pyplot as plt
import xtrack as xt
import xcoll as xc
import xobjects as xo
import xpart as xp
from pathlib import Path
import time
start_time = time.time()


def install_tidp(line, block_mvt=29e-3):
    tidp_ap_tot = 147e-3
    line.discard_tracker()
    tidp = xc.EverestCollimator(length=4.3, material=xc.materials.Carbon, jaw_L= tidp_ap_tot/2 + block_mvt, jaw_R = -tidp_ap_tot/2 + block_mvt)
    line.collimators.install(names=['tidp.11434'], elements=[tidp])
    return tidp

def install_tcsm(line):
    tcsm = xc.EverestCollimator(length=1.83, gap=5, material=xc.materials.Carbon) # length is 1.83
    line.collimators.install(names=['tcsm.51932'], elements=[tcsm])
    return tcsm

def lin_eq_params(x1, y1, x2, y2):
    delta = x1-x2
    delta_a = y1-y2
    delta_b = x1*y2-x2*y1

    a = delta_a/delta
    b = delta_b/delta
    return a, b

def offset_colls_calc(a, b, s_rel):
    return a*s_rel + b


#Parameters
num_turns = 3000
num_particles = 10_000

nemitt_x = 3.5e-6
nemitt_y = 3.5e-6
amplitude_adt = 0.2

context = xo.ContextCpu()
line = xt.Line.from_json('../../injection_lines/sps_with_aperture_inj_q20_beam_sagitta5.json')

line.vars['qph_setvalue'] = 0.5
line.vars['qpv_setvalue'] = 0.5
line.vars['qh_setvalue'] = line.vars['qx0']._value + 0.05
line.vars['qv_setvalue'] = line.vars['qy0']._value + 0.05

cavity_elements, cavity_names = line.get_elements_of_type(xt.Cavity)

for name in cavity_names:
    line[name].frequency = 200e6
    line[name].lag = 180
line['acl.31735'].voltage = 0 #setting 800 cav to 0V
line['actcse.31632'].voltage = 3.0e6


tcsm = install_tcsm(line)
tidp = install_tidp(line, block_mvt=29e-3)
offset_upstream = -3.314e-3
offset_downstream = -2.152e-3

tw = line.twiss()
idx_tidvg = np.where(tw.name=='tidvg.51872')[0][0]
ap_tidvg_x = 78.6e-3/2
ap_tidvg_y = 40.8e-3/2

# sigma_tidvg_x, sigma_tidvg_y = np.sqrt(tw.betx[idx_tidvg]*nemitt_x/tw.gamma0), np.sqrt(tw.bety[idx_tidvg]*nemitt_y/tw.gamma0)
# gap_x, gap_y = ap_tidvg_x/sigma_tidvg_x, ap_tidvg_y/sigma_tidvg_y

a,b = lin_eq_params(0, offset_upstream, 4.3, offset_downstream)
jaw_RU_positions = [offset_colls_calc(a,b, 0), offset_colls_calc(a,b, 2.5), offset_colls_calc(a,b, 3.5), offset_colls_calc(a,b, 4.0)]
jaw_RD_positions = [offset_colls_calc(a,b, 2.5), offset_colls_calc(a,b, 3.5), offset_colls_calc(a,b, 4.0), offset_colls_calc(a,b, 4.3)]

tidvg_1 = xc.EverestCollimator(length=2.5, material = xc.materials.Carbon, jaw_RU = -ap_tidvg_y + jaw_RU_positions[0], jaw_RD = -ap_tidvg_y + jaw_RD_positions[0], angle = 90, side = 'right') #it is graphite but apparently that dos not exist (except Molybdenium graphite)
tidvg_2 = xc.EverestCollimator(length=1.0, material = xc.materials.Aluminium, jaw_RU = -ap_tidvg_y + jaw_RU_positions[1], jaw_RD = -ap_tidvg_y + jaw_RD_positions[1], angle = 90, side = 'right')
tidvg_3 = xc.EverestCollimator(length=0.5, material = xc.materials.Copper, jaw_RU = -ap_tidvg_y + jaw_RU_positions[2], jaw_RD = -ap_tidvg_y + jaw_RD_positions[2], angle = 90, side = 'right')
tidvg_4 = xc.EverestCollimator(length=0.3, material = xc.materials.Tungsten, jaw_RU = -ap_tidvg_y + jaw_RU_positions[3], jaw_RD = -ap_tidvg_y + jaw_RD_positions[3], angle = 90, side = 'right')


line.discard_tracker()
center_drift = 0.35
begin_tidvg = tw.s[idx_tidvg] + center_drift
coll_names = ['tidvg.51872..1_C', 'tidvg.51872..2_Al', 'tidvg.51872..3_Cu', 'tidvg.51872..4_W']
line.collimators.install(names=coll_names, elements=[tidvg_1, tidvg_2, tidvg_3, tidvg_4], at_s=[begin_tidvg, begin_tidvg+2.5, begin_tidvg+3.5, begin_tidvg+4])


adt = xc.BlowUp.install(line, name=f'adt_H_blowup', at_s=line.get_s_position('adkcv.32171'), plane='H', stop_at_turn=num_turns,
                        amplitude=amplitude_adt, use_individual_kicks=True)

line.build_tracker()
tw= line.twiss()
line.collimators.assign_optics(twiss=tw, nemitt_x=nemitt_x, nemitt_y=nemitt_y)

adt.calibrate_by_emittance(nemitt=nemitt_x, twiss=tw)


for i in range(100):
    print(i)
    part = xp.generate_matched_gaussian_bunch(num_particles=num_particles, total_intensity_particles=2.2e11, nemitt_x=nemitt_x, nemitt_y=nemitt_y, sigma_z=0.224, line=line) #He does not like if quadrupoles are shifted/you cannot optimise the line


    line.discard_tracker()
    line.build_tracker(_context=xo.ContextCpu(omp_num_threads='auto'))

    line.scattering.enable()
    adt.activate()
    line.track(part, num_turns=num_turns, time=True, with_progress=1)
    adt.deactivate()
    line.scattering.disable()
    ThisLM = xc.LossMap(line, line_is_reversed=False, part=part, interpolation=False)
    ThisLM.to_json(file=f'LM_blowup_{i}.json')