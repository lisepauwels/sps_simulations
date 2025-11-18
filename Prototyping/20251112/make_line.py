import xtrack as xt
from pathlib import Path

env = xt.load('https://gitlab.cern.ch/acc-models/acc-models-sps/-/raw/2025/archive/SPS_LS2_2025-03-05.seq')
env.vars.load('https://gitlab.cern.ch/acc-models/acc-models-sps/-/raw/2025/strengths/lhc_q20.str')
# env.vars.load('https://gitlab.cern.ch/acc-models/acc-models-sps/-/raw/2025/strengths/lhc_q26.str')
# env.vars.load('https://gitlab.cern.ch/acc-models/acc-models-sps/-/raw/2025/strengths/ft_q26.str')

line = env['sps']
line.particle_ref = xt.Particles(mass0=xt.PROTON_MASS_EV, p0c=25.92e9)
# line.particle_ref = xt.Particles(mass0=xt.PROTON_MASS_EV, p0c=14e9)  # For Q26 Fixed Target

tt = line.get_table()

# Set RF
env['freq200'] = 200.2645e6
env['volt200'] = 4.5e6
env['lag200']  = 180  # Above transition
env['freq800'] = '4*freq200'
env['volt800'] = 0.5e6
env['lag800']  = 180  # Above transition
tt_ct = tt.rows['act.*']
line.set(tt_ct, frequency='freq200', voltage=f'volt200/{len(tt_ct)}', lag='lag200')
tt_cl = tt.rows['acl.*']
line.set(tt_cl, frequency='freq800', voltage=f'volt800/{len(tt_cl)}', lag='lag800')

# Set tune and chroma
env['qh_setvalue'] = 20.13
env['qv_setvalue'] = 20.18
# env['qh_setvalue'] = 26.13    # Q26
# env['qv_setvalue'] = 26.18
# env['qh_setvalue'] = 26.62    # FT
# env['qv_setvalue'] = 26.58
env['qph_setvalue'] = 0.5
env['qpv_setvalue'] = 0.5

# env.to_json(Path('/Users/lisepauwels/sps_simulations/injection_lines/sps_q20_inj.json'))
line.to_json(Path('/Users/lisepauwels/sps_simulations/injection_lines/sps_q20_inj.json'))
# env.to_json('sps_q26_inj.json')
# env.to_json('sps_ft_q26_inj.json')