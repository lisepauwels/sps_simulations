import numpy as np
import xtrack as xt
import xpart as xp
import xcoll as xc
import xobjects as xo
import json
import sys

job_id = int(sys.argv[1])

#Information
num_particles = 10
num_turns = 1_000_000
nemitt_x = 2e-6
nemitt_y = 2e-6
sigma_z = 00.224

rescale_factors = {'x_norm': 30,
                   'px_norm': 30,
                   'y_norm': 30,
                   'py_norm': 30,
                   'zeta': 3*sigma_z,
                   'delta': 5e-3}

#Line
line = xt.Line.from_json('sps_q20_inj.json')
tt = line.get_table()
tw = line.twiss()

context = xo.ContextCpu()
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

env = line.env
monitor = xt.ParticlesMonitor(num_particles=num_particles, start_at_turn=0, stop_at_turn=num_turns)
env.elements['monitor_start'] = monitor
line.insert([env.place('monitor_start', at=0)])

#Particles
with open('initial_conditions_uniform_ring_6d.json', 'r') as f:
    initial_conditions = json.load(f)

part = line.build_particles(
    x_norm=initial_conditions['x_norm'][job_id], px_norm=initial_conditions['px_norm'][job_id],
    y_norm=initial_conditions['y_norm'][job_id], py_norm=initial_conditions['py_norm'][job_id],
    zeta=initial_conditions['zeta'][job_id],
    delta=initial_conditions['delta'][job_id],
    nemitt_x=2e-6, nemitt_y=2e-6, # normalized emittances
    )

line.track(part, num_turns=num_turns, time=True, with_progress=True)

dict_monitor={'x' : monitor.x.tolist(), 'y' : monitor.y.tolist(), 'px' : monitor.px.tolist(), 'py' : monitor.py.tolist(), 'zeta' : monitor.zeta.tolist(), 'delta' : monitor.delta.tolist(), 'state': monitor.state.tolist()}
dict_part = {'x' : part.x.tolist(), 'y' : part.y.tolist(), 'px' : part.px.tolist(), 'py' : part.py.tolist(), 'zeta' : part.zeta.tolist(), 'delta' : part.delta.tolist(), 'state': part.state.tolist(), 'at_turn': part.at_turn.tolist(), 'particle_id': part.particle_id.tolist(), 'at_element': part.at_element.tolist()}

with open(f'monitor.json', 'w') as fout:
    json.dump(dict_monitor, fout, indent=4)

with open(f'particles.json', 'w') as fout:
    json.dump(dict_part, fout, indent=4)