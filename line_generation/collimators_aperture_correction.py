import xtrack as xt
line = xt.Line.from_json('../injection_lines/sps_with_aperture_inj_q20_beam_sagitta3.json')
env = line.env

tt = line.get_table()
tw = line.twiss()

s_start_tidp = line.get_s_position('tidp.11434..0')
s_start_tcsm = line.get_s_position('tcsm.51932..0')
line.remove(tt.rows['tidp.*'].name)
line.remove(tt.rows['tcsm.*'].name)

line.insert(env.place('tidp.11434', at=s_start_tidp), s_tol=1e-6)
line.insert(env.place('tcsm.51932', at=s_start_tcsm), s_tol=1e-6)

env.elements['tidp.11434.a_aper'] = xt.LimitEllipse(a=0.1, b=0.1)
env.elements['tidp.11434.b_aper'] = xt.LimitEllipse(a=0.1, b=0.1)
env.elements['tcsm.51932.a_aper'] = xt.LimitEllipse(a=0.1, b=0.1)
env.elements['tcsm.51932.b_aper'] = xt.LimitEllipse(a=0.1, b=0.1)

line.insert([env.place('tidp.11434.a_aper', at='tidp.11434' + '@start'),
             env.place('tidp.11434.b_aper', at='tidp.11434' +'@end'),
             env.place('tcsm.51932.a_aper', at='tcsm.51932'+'@start'),
             env.place('tcsm.51932.b_aper', at='tcsm.51932' +'@end')], s_tol=1e-6)

line.to_json('../injection_lines/sps_with_aperture_inj_q20_beam_sagitta4.json')