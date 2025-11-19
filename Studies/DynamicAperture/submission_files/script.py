import numpy as np
import xtrack as xt
import xpart as xp
import xcoll as xc
import xobjects as xo
import json
import sys
import pyarrow as pa
import pyarrow.parquet as pq

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
    x_norm=initial_conditions['x_norm'][job_id]*rescale_factors['x_norm'], px_norm=initial_conditions['px_norm'][job_id]*rescale_factors['px_norm'],
    y_norm=initial_conditions['y_norm'][job_id]*rescale_factors['y_norm'], py_norm=initial_conditions['py_norm'][job_id]*rescale_factors['py_norm'],
    zeta=initial_conditions['zeta'][job_id]*rescale_factors['zeta'],
    delta=initial_conditions['delta'][job_id]*rescale_factors['delta'],
    nemitt_x=2e-6, nemitt_y=2e-6, # normalized emittances
    )

part_dict = {pid + job_id*num_particles: {'x': [part.x[part.particle_id==pid][0].copy()], 'px': [part.px[part.particle_id==pid][0].copy()],
                                          'y': [part.y[part.particle_id==pid][0].copy()], 'py': [part.py[part.particle_id==pid][0].copy()],
                                          'zeta' : [part.zeta[part.particle_id==pid][0].copy()], 'delta' : [part.delta[part.particle_id==pid][0].copy()],
                                            'state': [part.state[part.particle_id==pid][0].copy()], 'at_turn': [0], 'particle_id': [pid], 'at_element': [0]} for pid in part.particle_id}

for nn_saving in range(int(num_turns/1000)):
    line.track(part, num_turns=1000, time=True, with_progress=True)
    for pid in part.particle_id:
        dict_id = job_id * num_particles + pid
        for key in part_dict[dict_id].keys():
            part_dict[dict_id][key].append(part.__getattribute__(key)[part.particle_id==pid][0].copy())

columns = {}
array_length = 1001  # fixed size of each array

for key in part_dict[0]:  # iterate over keys
    # concatenate arrays for all pids for this key
    concatenated = np.concatenate([part_dict[pid][key] for pid in part_dict])
    # create FixedSizeListArray
    columns[key] = pa.FixedSizeListArray.from_arrays(concatenated, array_length)

# Optional: create a 'pid' column
pid_column = pa.array(list(part_dict.keys()))

# Build table
table = pa.table({**{"pid": pid_column}, **columns})
pq.write_table(table, "particles.parquet", compression="gzip")