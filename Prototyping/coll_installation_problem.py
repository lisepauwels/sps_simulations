import numpy as np
import matplotlib.pyplot as plt
import xtrack as xt
import xcoll as xc

# Functions
def install_tidp(line, block_mvt=29e-3):
    tidp_ap_tot = 147e-3
    line.discard_tracker()
    tidp = xc.EverestCollimator(length=4.3, material=xc.materials.Carbon, jaw_L= tidp_ap_tot/2 + block_mvt, jaw_R = -tidp_ap_tot/2 + block_mvt)
    line.collimators.install(names=['tidp.11434'], elements=[tidp])
    return tidp

def install_tcsm(line):
    tcsm = xc.EverestCollimator(length=1.83, gap=5, material=xc.materials.Carbon) # length is 1.83
    line.collimators.install(names=['tcsm.51932'], elements=[tcsm])
    return tcsm

def install_offmom_bpms_colls(line, exn=3.5e-6, nrj=21, pmass=0.938, bucket_height=3e-3, n_buckets=2):
    tw = line.twiss()
    tt = line.get_table()
    mask_disp = 5*np.sqrt(tw.betx*exn*pmass/nrj)+n_buckets*bucket_height*tw.dx > 0.025
    mask_bpm = ['bp' in name for name in tt.name]
    mask_aper = np.array(['aper' in name for name in tt.name])
    offmom_bpms = tt.name[mask_disp & mask_bpm & ~mask_aper]
    colls = []
    aper_to_remove = []
    for nn in offmom_bpms:
        aper_to_remove.append(f'{nn}.a_aper')
        aper_to_remove.append(f'{nn}.b_aper')
        if line[nn+'.a_aper'].__class__.__name__ == 'LimitEllipse':
            jaw = line[nn+'.a_aper'].a
        else:
            jaw = line[nn+'.a_aper'].max_x
        
        colls.append(xc.EverestCollimator(length=line[nn].length, material=xc.materials.Beryllium, jaw=jaw))
    line.remove(aper_to_remove)
    line.collimators.install(names=offmom_bpms, elements=colls)
    return colls

def remove_offmom_bpms_apers(line, exn=3.5e-6, nrj=21, pmass=0.938, bucket_height=3e-3, n_buckets=2):
    "Remove apertures of off-momentum BPMs which give flanges as bottlenecks"
    tw = line.twiss()
    tt = line.get_table()
    mask_disp = 5*np.sqrt(tw.betx*exn*pmass/nrj)+n_buckets*bucket_height*tw.dx > 0.025
    mask_bpm = ['bp' in name for name in tt.name]
    mask_aper = np.array(['aper' in name for name in tt.name])
    offmom_bpms = tt.name[mask_disp & mask_bpm & ~mask_aper]
    aper_to_remove = [f'{name}{suffix}' for name in offmom_bpms for suffix in ('.a_aper', '.b_aper')]
    line.remove(aper_to_remove)

# Load the line
line = xt.Line.from_json('../injection_lines/sps_with_aperture_inj_q20_beam_sagitta4.json')

remove_offmom_bpms_apers(line, exn=3.5e-6, nrj=21, pmass=0.938, bucket_height=3e-3, n_buckets=2)
tt = line.get_table()
# tw = line.twiss()

#shift VEB apertures by 5.3 mm to account for the sagitta
veb_b_apers = tt.rows['veb.*.b_aper'].name
for name in veb_b_apers:
    line[name].shift_x += 5.3e-3

veb_a_apers = tt.rows['veb.*.a_aper'].name
for name in veb_a_apers:
    line[name].shift_x += 5.3e-3
#Houdt de a aperture steek?
tt = line.get_table()
tw = line.twiss()

print('Initial table:')
print(tt.rows['vcak.13501.a_aper<<5':'vcak.13501.a_aper>>5'])

#Changed flanges numbers
changed = [10110, 11110, 11310, 12510, 13510, 20910, 21110, 22510, 23510, 30110, 30910,
32510, 33510, 40110, 40910, 41110, 42510, 42710, 51110, 52510, 53510, 60110,
61110, 62510, 63510]

# Adding apertures
env = line.env
insertions = []
for qd_number in changed:
    flange_number = qd_number - 9
    
    aper_start = f'vcak.{flange_number}.a_aper'
    aper_end = f'vcak.{flange_number}.b_aper'

    for nn, ee in zip(tt.rows[aper_start:aper_end].name, tt.rows[aper_start:aper_end].element_type):
        if not ee.startswith('Limit') and not ee.startswith('Drift') and not ee.startswith('Marker'):
            env.elements[f'{nn}_aper_enter'] = line['vcak.13501.a_aper'].copy()
            env.elements[f'{nn}_aper_exit'] = line['vcak.13501.b_aper'].copy()
            insertions.append(env.place(f'{nn}_aper_enter', at=f'{nn}@start'))
            insertions.append(env.place(f'{nn}_aper_exit', at=f'{nn}@end'))
line.insert(insertions, s_tol=1e-6)
tt = line.get_table()
print('After adding missing apertures:')
print(tt.rows['vcak.13501.a_aper<<5':'vcak.13501.a_aper>>5'])

#Start and end flange aperetures
start_flange_apers = []
end_flange_apers = []
for qd_number in changed:
    flange_number = qd_number - 9
    
    aper_start = f'vcak.{flange_number}.a_aper'
    aper_end = f'vcak.{flange_number}.b_aper'

    for nn, ee in zip(tt.rows[f'{aper_start}>>1':aper_end].name, tt.rows[f'{aper_start}>>1':aper_end].element_type):
        if ee.startswith('Drift') or ee.startswith('Marker'):
            continue
        elif ee.startswith('Limit'):
            next_aper = nn
            break
        else:
            raise ValueError(f'Unexpected element type {ee} for element {nn}')
    end_flange_apers.append(next_aper)
    start_flange_apers.append(aper_start)

L1 = 34e-3
L2 = 70e-3

r1 = 41.5e-3
r2 = 60e-3-1.5e-3
r3 = 51.5e-3
flange_numbers = [nn-9 for nn in changed]

colls = []
colls_names = []
colls_positions = []
line.discard_tracker()
for nn, start, end in zip(flange_numbers, start_flange_apers, end_flange_apers):
    colls_positions += [line.get_s_position(start), line.get_s_position(start)+L1, line.get_s_position(start)+L1+L2]
    colls_names += [f'vcak.{nn}.coll..0', f'vcak.{nn}.coll..1', f'vcak.{nn}.coll..2']
    
    colls += [xc.EverestCollimator(length=L1, material=xc.materials.Glidcop, jaw=r1-5.3e-3),
                xc.EverestCollimator(length=L2, material=xc.materials.Glidcop, jaw=r2),
                xc.EverestCollimator(length=line.get_s_position(end)-line.get_s_position(start)-L1-L2, material=xc.materials.Glidcop, jaw=r3)]
line.collimators.install(names=colls_names, elements=colls, at_s=colls_positions)

tt = line.get_table()
print('After collimator installation:')
print(tt.rows['vcak.13501.a_aper<<5':'vcak.13501.a_aper>>5'])