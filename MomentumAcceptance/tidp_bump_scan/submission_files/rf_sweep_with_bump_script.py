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

bump = float(sys.argv[1])*1e-3

#Preping line for bump
env = line.env

line['bump.11207'] = 0
line['bump.11407'] = 0
line['bump.11607'] = 0
line['bump.12207'] = 0

line.ref['mdh.11207'].knl[0] += line.vars['bump.11207']
line.ref['mdh.11407'].knl[0] += line.vars['bump.11407']
line.ref['mdh.11607'].knl[0] += line.vars['bump.11607']
line.ref['mdh.12207'].knl[0] += line.vars['bump.12207']


#Context and parameters
context = xo.ContextCpu()

num_particles  = 2000
plane = 'DPneg'
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

tw = line.twiss()
opt = line.match(
    solve=False,
    start='mdh.11007',
    end='mdhw.11732',
    init=tw,
    vary=[
        xt.VaryList(['bump.11207', 'bump.11407', 'bump.11607'], step=1e-8, tag='bump',)
    ],
    targets = [
        xt.Target('x', bump, at='tidp.11434'),
        xt.TargetSet(['x', 'px'], value=tw, at='mdhw.11732')
    ]
    )
opt.run_jacobian(10)


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