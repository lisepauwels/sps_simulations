"""
Expected results (from test): 
    - particles are all lost at elements 'bpcn.12508.a_aper' (index 8400) and  'bpcn.61108.a_aper' (66905)
    - losses only start around turn 2500, so really off momentum aperture bottleneck
    - Only 3 particles out of 5000 survived
"""

import numpy as np
from pathlib import Path
import time
import matplotlib.pyplot as plt
start_time = time.time()

import xobjects as xo
import xtrack as xt
import xpart as xp
import xobjects as xo
import xcoll as xc

import apertls
from matplotlib.colors import LogNorm

#rf sweep settings
beam = 1
plane = 'DNeg'#'DPpos'

num_particles  = 5000
sweep          = 3500
sweep          = -abs(sweep) if plane == 'DPpos' else abs(sweep)
num_turns=6000

nemitt_x = 3.5e-6
nemitt_y = 3.5e-6

#Loading line and setting all cavities to 200 (even 800 cavities) because rf sweep not implemented
line = xt.Line.from_json('../injection_lines/sps_with_aperture_inj_q20_beam_sagitta.json')
cavity_elements, cavity_names = line.get_elements_of_type(xt.Cavity)
for name in cavity_names:
    line[name].frequency = 200e6
    line[name].lag = 180

line['acl.31735'].voltage = 0

#optics
tw = line.twiss()
line.collimators.assign_optics()

#particles
part = xp.generate_matched_gaussian_bunch(nemitt_x=nemitt_x,
                                          nemitt_y=nemitt_y,
                                          sigma_z=0.224, num_particles=num_particles, line=line)

line.build_tracker(_context=xo.ContextCpu(omp_num_threads='25'))

#rf sweep
rf_sweep = xc.RFSweep(line)
rf_sweep.info(sweep=sweep, num_turns=num_turns)

#tracking
line.scattering.enable()
rf_sweep.track(sweep=sweep, particles=part, num_turns=num_turns, time=True, with_progress=5)
line.scattering.disable()
print(f"Done sweeping RF in {line.time_last_track:.1f}s.")


#Plot
turn_bins_resolution = 1000
turn_min, turn_max = 0, num_turns
turn_bins = np.linspace(turn_min, turn_max, turn_bins_resolution + 1)

element_bin_resolution = 1000
element_min, element_max = 0, len(line.element_names)
element_bins = np.linspace(element_min, element_max, element_bin_resolution + 1)

hist2d, element_edges, turn_edges = np.histogram2d(
    part.at_element[part.state<=0], part.at_turn[part.state<=0],
    bins=[element_bins, turn_bins]
)

plt.figure(figsize=(10, 6))
plt.imshow(hist2d, aspect='auto', interpolation='nearest',
           extent=[turn_bins[0], turn_bins[-1], element_bins[0], element_bins[-1]],
           origin='lower', norm=LogNorm())

plt.colorbar(label='Number of particles (log scale)')
plt.xlabel('Turn at which particle is lost')
plt.ylabel('Element index')
plt.title('Loss Map: Turn vs Element')

plt.tight_layout()
plt.show()