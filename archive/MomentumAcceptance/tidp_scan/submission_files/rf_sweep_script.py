import numpy as np
from pathlib import Path
import sys
import json

import xobjects as xo
import xtrack as xt
import xpart as xp
import xobjects as xo
import xcoll as xc

line = xt.Line.from_json('sps_with_aperture_inj_q20_beam_sagitta2.json')

plane = str(sys.argv[1])
chroma = float(sys.argv[2])
if plane not in ['DPpos', 'DPneg']:
    raise ValueError("Plane must be either 'DPpos' or 'DPneg'.")

#Changing tune
line.vars['qh_setvalue'] = line.vars['qx0']._value + 0.05
line.vars['qv_setvalue'] = line.vars['qy0']._value + 0.05
# Setting the chromaticity
line.vars['qph_setvalue'] = chroma
line.vars['qpv_setvalue'] = chroma

#Context and parameters
context = xo.ContextCpu()

num_particles  = 2000
sweep = 6000
sweep = -abs(sweep) if plane == 'DPpos' else abs(sweep)
num_turns = 6000

#Setting cavities to the same frequency and phase, plus setting the voltage
cavity_elements, cavity_names = line.get_elements_of_type(xt.Cavity)

for name in cavity_names:
    line[name].frequency = 200e6
    line[name].lag = 180
line['actcse.31632'].voltage = 3.5e6

#Installing TIDP
tidp_ap_tot = 147
block_mvt = 29

tidp = xc.EverestCollimator(length=4.3, material=xc.materials.Carbon, jaw_L= tidp_ap_tot/2 + block_mvt, jaw_R = -tidp_ap_tot/2 + block_mvt)
line.collimators.install(names=['tidp.11434'], elements=[tidp])

line.build_tracker()
part = xp.generate_matched_gaussian_bunch(nemitt_x=3.5e-6,
                                          nemitt_y=3.5e-6,
                                          sigma_z=0.224, num_particles=num_particles, line=line)

rf_sweep = xc.RFSweep(line)
rf_sweep.info(sweep=sweep, num_turns=num_turns)

line.scattering.enable()
rf_sweep.track(sweep=sweep, particles=part, num_turns=num_turns, time=True, with_progress=5)
line.scattering.disable()

with open('part.json', 'w') as fid:
    json.dump(part.to_dict(), fid, cls=xo.JEncoder)