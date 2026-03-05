from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import xtrack as xt
import xobjects as xo
import xpart as xp
import xcoll as xc
import json

#Line with set cavities, qx = 20.13, qy=20.18, xi=0.5
line = xt.load('sps_inj_q20_aper_momentum_scan.json')
env = line.env

#Context and parameters
context = xo.ContextCpu()

xi = 0.5 #normalised chroma -- same for qx and qy
qx = 20.13
qy = 20.18

num_particles  = 2000
num_turns = 6000

sweep = 6000
plane = 'DPneg'
sweep = -abs(sweep) if plane == 'DPpos' else abs(sweep)

nemitt_x = 2e-6
nemitt_y = 2e-6
sigma_z = 0.224

#Optimisation if needed
env.vars['qph_setvalue'] = xi
env.vars['qpv_setvalue'] = xi
opt = line.match(
    method='6d', # <- passed to twiss
    vary=[
        xt.VaryList(['kqf0', 'kqd0'], step=1e-8, tag='quad'),
        xt.VaryList(['qph_setvalue', 'qpv_setvalue'], step=1e-4, tag='sext'),
    ],
    targets = [
        xt.TargetSet(qx=qx, qy=qy, tol=1e-6, tag='tune'),
        xt.TargetSet(dqx=xi*qx, dqy=xi*qy, tol=1e-2, tag='chrom'),
    ])

#Installing TIDP (off-momentum block/collimator)
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

line.discard_tracker()
line.build_tracker(_context=xo.ContextCpu(omp_num_threads='auto'))
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

with open(f'death_turns_{xi}_{plane}.json', 'w') as fid:
    json.dump(dico, fid, indent=4)