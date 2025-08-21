import numpy as np
import xtrack as xt
import shutil
from cpymad.madx import Madx

mad = Madx()
mad.call('sps.seq')
mad.beam()
mad.use('SPS')

line = xt.Line.from_madx_sequence(
    mad.sequence.SPS,
    deferred_expressions=True,
)

line.env.vars.load_madx('lhc_q20.str')
line['acl.31735'].frequency = 800e6
line['acl.31735'].voltage = 2 * 0.18e6
line['acl.31735'].lag = 180
line['actcse.31632'].frequency = 200e6
line['actcse.31632'].voltage = 4.5e6
line['actcse.31632'].lag = 180
line.particle_ref = xt.Particles.reference_from_pdg_id('proton',p0c=25.92e9)

tt = line.get_table()
tw_ref = line.twiss()

#Introduce doglegs
line['qd.51710'].shift_y = -5.273e-3
line['qfa.51810'].shift_y = -17.369e-3
line['qd.51910'].shift_y = -5.273e-3
line['qd.11710'].shift_x = -4.80e-3
line['qf.11810'].shift_x = -2.97e-3
line['qda.11910'].shift_x = -4.80e-3

tw_without_corr = line.twiss()

#Orbit correction
tt_monitors = tt.rows['bp.*'].rows['.*(?<!_entry)$'].rows['.*(?<!_exit)$']
line.steering_monitors_x = tt_monitors.name
line.steering_monitors_y = tt_monitors.name

tt_h_correctors = tt.rows['mdh\..*'].rows['.*h\..*']
mask_ap_h = np.array([el.startswith('Limit') for el in tt_h_correctors.element_type])
line.steering_correctors_x = tt_h_correctors.name[~mask_ap_h]

tt_v_correctors = tt.rows['mdv\..*'].rows['.*v\..*']
mask_ap_v = np.array([el.startswith('Limit') for el in tt_v_correctors.element_type])
line.steering_correctors_y = tt_v_correctors.name[~mask_ap_v]

orbit_correction = line.correct_trajectory(twiss_table=tw_ref,n_micado=5, n_iter=10)

#Plot orbit after correction for verification
tw_after = line.twiss()
tw_after.plot('x')
tw_after.plot('y')

# Save the line with the orbit correction
line.to_json('sps_without_aperture_inj_q20.json')