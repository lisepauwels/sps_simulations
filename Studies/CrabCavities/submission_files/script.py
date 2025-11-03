import numpy as np
import matplotlib.pyplot as plt
import sys

import xtrack as xt
import xpart as xp
import xobjects as xo
import xcoll as xc
from pathlib import Path
import json
import time
start_time = time.time()

#Functions
def install_tidp(line, block_mvt=29e-3):
    tidp_ap_tot = 147e-3
    line.discard_tracker()
    tidp = xc.EverestCollimator(length=4.3, material=xc.materials.Carbon, jaw_L= tidp_ap_tot/2 + block_mvt, jaw_R = -tidp_ap_tot/2 + block_mvt)
    line.collimators.install(names=['tidp.11434'], elements=[tidp])
    return tidp

def install_tcsm(line, gap=5):
    tcsm = xc.EverestCollimator(length=1.83, gap=gap, material=xc.materials.Carbon) # length is 1.83
    line.collimators.install(names=['tcsm.51932'], elements=[tcsm])
    return tcsm


line = xt.Line.from_json('off_mom_scan_line.json')
tt = line.get_table()

crab_voltage = float(sys.argv[1])
lag = float(sys.argv[2])
coll_gap = float(sys.argv[3])

num_particles = 10000
plane = 'H'
start_at_turn= 100
nemitt_x = 2e-6
nemitt_y = 2e-6
ramping_turns = 100
use_individual_kicks = True

adt = xc.BlowUp.install(line, name=f'adt_{plane}_blowup', at_s=line.get_s_position('adkcv.32171'), plane=plane, stop_at_turn=num_turns,
                        amplitude=0.0005, use_individual_kicks=use_individual_kicks, start_at_turn=start_at_turn)

tw = line.twiss()
tidp = install_tidp(line, block_mvt=29e-3)
tcsm = install_tcsm(line, gap=coll_gap)
line.collimators.assign_optics(twiss=tw, nemitt_x=nemitt_x, nemitt_y=nemitt_y)

part = xp.generate_matched_gaussian_bunch(nemitt_x=nemitt_x,
                                          nemitt_y=nemitt_y,
                                          sigma_z=0.224, num_particles=num_particles, line=line)

adt.calibrate_by_emittance(nemitt=nemitt_x, twiss=tw)


#Tracking
line.scattering.enable()
print('Ramping crab cavities')
for turn in range(1,101):
    if turn % 10 == 0:
        print(f'  Turn {turn}')
    line['acfcah.61738'].crab_voltage = crab_voltage * turn / 100
    line['acfcah.61739'].crab_voltage = crab_voltage * turn / 100
    line.track(part, num_turns=1, with_progress=False)

print(line['acfcah.61738'].crab_voltage)
print(line['acfcah.61739'].crab_voltage)
print('Crab cavities ramped up.')
print('Ramping up ADT up to 0.05 in 100 turns')

adt.activate()
for turn in range(1,101):
    if turn % 10 == 0:
        print(f'  Turn {turn}')
    adt.amplitude = 0.0005 * turn
    line.track(part, num_turns=1, with_progress=False)

print('First ADT ramp up done! Tracking 400 turns...')
line.track(part, num_turns=400, with_progress=True)

for turn in range(1,500):
    if turn % 50 == 0:
        print(f'  Turn {turn}')
    adt.amplitude = 0.05 + 0.0001 * turn
    line.track(part, num_turns=1, with_progress=False)

print('Second ADT ramp up done! Tracking remaining 2500 turns...')
line.track(part, num_turns=2500, with_progress=True)
adt.deactivate()
line.scattering.disable()

#Saving
ThisLM = xc.LossMap(line = line, line_is_reversed=False, part=part, interpolation=False)
ThisLM.to_json(f'LM.json')

part_dict = {'state' : part.state,
             's' : part.s,
             'at_element': part.at_element,
             'at_turn' : part.at_turn,
             'id_part' : part.id_part}

json.dump(part_dict, open('particle_dict.json', 'w'), indent=4)