import numpy as np
import matplotlib.pyplot as plt
import xtrack as xt
import xpart as xp
import xcoll as xc
import xobjects as xo
import sys
import json

start_ele = int(sys.argv[1])

def install_tidp(line, block_mvt=29e-3):
    tidp_ap_tot = 147e-3
    line.discard_tracker()
    tidp = xc.EverestCollimator(length=4.3, material=xc.materials.Carbon, jaw_L= tidp_ap_tot/2 + block_mvt, jaw_R = -tidp_ap_tot/2 + block_mvt)
    line.collimators.install(names=['tidp.11434'], elements=[tidp])
    return tidp


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

num_particles  = 100
plane = 'DPneg'
sweep = 6000
sweep = -abs(sweep) if plane == 'DPpos' else abs(sweep)
num_turns = 6000


tidp = install_tidp(line)

tt = line.get_table()
tw = line.twiss()

#Particles
x_spacing = np.linspace(-0.025, 0.025, int(np.sqrt(num_particles)))
y_spacing = np.linspace(-0.025, 0.025, int(np.sqrt(num_particles)))

X, Y = np.meshgrid(x_spacing, y_spacing, indexing='xy')
x_norm = X.ravel()
y_norm = Y.ravel()

px_norm = np.zeros_like(x_norm)
py_norm = np.zeros_like(x_norm)
zeta = np.ones_like(x_norm)*tw.particle_on_co.zeta
delta = np.ones_like(x_norm)*tw.particle_on_co.delta

part = line.build_particles(x_norm=x_norm, px_norm=px_norm, y_norm=y_norm, py_norm=py_norm, nemitt_x=3.5e-6, nemitt_y=3.5e-6, zeta=zeta, delta=delta)

rf_sweep = xc.RFSweep(line)
rf_sweep.info(sweep=sweep, num_turns=num_turns)

line.discard_tracker()
line.build_tracker(_context=xo.ContextCpu(omp_num_threads='auto'))
line.scattering.enable()
rf_sweep.track(sweep=sweep, particles=part, num_turns=num_turns, time=True, with_progress=True, ele_start=start_ele*100)
line.scattering.disable()

# Get counts
elems, elem_counts = np.unique(part.at_element, return_counts=True)
turns, turn_counts = np.unique(part.at_turn, return_counts=True)

# Convert to JSON-serializable dict
data = {
    "at_element": {
        "values": elems.tolist(),
        "counts": elem_counts.tolist()
    },
    "at_turn": {
        "values": turns.tolist(),
        "counts": turn_counts.tolist()
    }
}

# Save to file
with open(f"counts_json_files/counts_start_{start_ele}.json", "w") as f:
    json.dump(data, f, indent=2)

ThisLM = xc.LossMap(line, line_is_reversed=False, part=part, interpolation=False)
ThisLM.to_json(file=f'LM_json_files/LM_start_{start_ele}.json')