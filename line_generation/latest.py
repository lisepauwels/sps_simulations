import xtrack as xt
line = xt.Line.from_json('../acc-models-sps/xsuite/sps_with_aperture.json')
line.env.vars.load_madx('../acc-models-sps/strengths/lhc_q20.str')
line['acl.31735'].frequency = 800e6
line['acl.31735'].voltage = 2 * 0.18e6
line['acl.31735'].lag = 180
line['actcse.31632'].frequency = 200e6
line['actcse.31632'].voltage = 4.5e6
line['actcse.31632'].lag = 180
line.particle_ref = xt.Particles.reference_from_pdg_id('proton',p0c=25.92e9)
line.to_json('../acc-models-sps/xsuite/sps_with_aperture_inj_q20.json')
