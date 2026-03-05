import numpy as np
from pathlib import Path
import sys
import json

import xobjects as xo
import xtrack as xt
import xpart as xp
import xobjects as xo
import xcoll as xc

line = xt.load(str(sys.argv[1]))
env = line.env
xi_x = float(sys.argv[2])
xi_y = float(sys.argv[3])
plane = str(sys.argv[4])
if plane not in ['DPpos', 'DPneg']:
    raise ValueError("Plane must be either 'DPpos' or 'DPneg'.")


qx = 20.13
qy = 20.18
#Context and parameters
context = xo.ContextCpu()

num_particles  = 2000
sweep = 6000
sweep = -abs(sweep) if plane == 'DPpos' else abs(sweep)
num_turns = 6000
nemitt_x = 2e-6
nemitt_y = 2e-6
sigma_z = 0.224
sweep_per_turn = sweep/num_turns

#Matching tune and chroma for error variant
env.vars['qph_setvalue'] = xi_x
env.vars['qpv_setvalue'] = xi_y
opt = line.match(
    method='6d', # <- passed to twiss
    vary=[
        xt.VaryList(['kqf0', 'kqd0'], step=1e-8, tag='quad'),
        xt.VaryList(['qph_setvalue', 'qpv_setvalue'], step=1e-4, tag='sext'),
    ],
    targets = [
        xt.TargetSet(qx=qx, qy=qy, tol=1e-6, tag='tune'),
        xt.TargetSet(dqx=xi_x*qx, dqy=xi_y*qy, tol=1e-2, tag='chrom'),
    ])


#Installing TIDP
tidp_ap_tot = 147
block_mvt = 29

line.discard_tracker()
tidp = xc.EverestCollimator(length=4.3, material=xc.materials.Carbon, jaw_L= tidp_ap_tot/2 + block_mvt, jaw_R = -tidp_ap_tot/2 + block_mvt)
line.collimators.install(names=['tidp.11434'], elements=[tidp])

line.build_tracker()

#particles
part = xp.generate_matched_gaussian_bunch(nemitt_x=nemitt_x,
                                          nemitt_y=nemitt_y,
                                          sigma_z=sigma_z, num_particles=num_particles, line=line)

rf_sweep = xc.RFSweep(line)
sweep_per_turn = -abs(sweep_per_turn) if plane == 'DPpos' else abs(sweep_per_turn)
rf_sweep.prepare(sweep_per_turn=sweep_per_turn)
rf_sweep.info()

# Track during RF sweep:
line.scattering.enable()
line.track(particles=part, num_turns=num_turns, time=True, with_progress=5)
line.scattering.disable()
print(f"Done sweeping RF in {line.time_last_track:.1f}s.")

# Save results
dico = {'sweep_per_turn': sweep_per_turn,
        'at_turn' : part.at_turn.copy().tolist()}

filename = f'death_turns_xi_{xi_x}_{xi_y}_{plane}.json'

with open(filename, 'w') as fid:
    json.dump(dico, fid, indent=4)