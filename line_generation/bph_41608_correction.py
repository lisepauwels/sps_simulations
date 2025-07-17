import xtrack as xt

line = xt.Line.from_json('../injection_lines/sps_with_aperture_inj_q20_beam_sagitta4.json')

tt = line.get_table()
tw = line.twiss()

env = line.env
s_bph = line.get_s_position('bph.41607..0')
s_a_aper = line.get_s_position('bph.41607.a_aper')
s_b_aper = line.get_s_position('bph.41607.b_aper')
elem = line['bph.41607'].copy()
aper = line['bph.41607.a_aper'].copy()

line.remove(tt.rows['bph.41607.*'].name)

env.elements['bph.41608'] = elem
env.elements['bph.41608.a_aper'] = aper
env.elements['bph.41608.b_aper'] = aper.copy()

line.insert(env.place('bph.41608', at=s_bph, anchor='start'), s_tol=1e-6)
line.insert([env.place('bph.41608.a_aper', at=s_a_aper),
            env.place('bph.41608.b_aper', at=s_b_aper)], s_tol=1e-6)

line.to_json('../injection_lines/sps_with_aperture_inj_q20_beam_sagitta5.json')