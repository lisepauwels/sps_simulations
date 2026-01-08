import numpy as np
from pathlib import Path
import sys
import json

import xobjects as xo
import xtrack as xt
import xpart as xp
import xobjects as xo
import xcoll as xc

line = xt.Line.from_json(str(sys.argv[1]))
plane = str(sys.argv[2])

if plane not in ['DPpos', 'DPneg']:
    raise ValueError("Plane must be either 'DPpos' or 'DPneg'.")


#Context and parameters
context = xo.ContextCpu()

num_particles  = 2000
sweep = 6000
sweep = -abs(sweep) if plane == 'DPpos' else abs(sweep)
num_turns = 6000
nemitt_x = 2e-6
nemitt_y = 2e-6
sigma_z = 0.224


#Installing TIDP
tidp_ap_tot = 147
block_mvt = 29

tidp = xc.EverestCollimator(length=4.3, material=xc.materials.Carbon, jaw_L= tidp_ap_tot/2 + block_mvt, jaw_R = -tidp_ap_tot/2 + block_mvt)
line.collimators.install(names=['tidp.11434'], elements=[tidp])

line.build_tracker()

#particles
part = xp.generate_matched_gaussian_bunch(nemitt_x=nemitt_x,
                                          nemitt_y=nemitt_y,
                                          sigma_z=sigma_z, num_particles=num_particles, line=line)

rf_sweep = xc.RFSweep(line)
rf_sweep.prepare(sweep_per_turn=sweep/num_turns)
rf_sweep.info()

# Track during RF sweep:
line.scattering.enable()
line.track(particles=part, num_turns=num_turns, time=True, with_progress=5)
line.scattering.disable()
print(f"Done sweeping RF in {line.time_last_track:.1f}s.")

# Save results
sweep_per_turn = sweep/num_turns
dico = {'sweep_per_turn': sweep_per_turn,
        'at_turn' : part.at_turn.copy().tolist()}

with open(f'death_turns.json', 'w') as fid:
    json.dump(dico, fid, indent=4)
