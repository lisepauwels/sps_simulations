import numpy as np
import matplotlib.pyplot as plt
import xtrack as xt
import xpart as xp
import xobjects as xo
import xcoll as xc
from pathlib import Path
import json


def create_bump(line, tw, at, pos, scale=1):
    left, mid, right = pos
    all_correctors = list(tw.rows['mdh\..*'].name)
    correctors  = (all_correctors + list(tw.rows[:mid].rows['mdh\..*'].name))[-2:]  # To allow wrapping around line
    correctors += (list(tw.rows[mid:].rows['mdh\..*'].name) + all_correctors)[:2]
    corrector_knobs = [f"kmdh{nn.split('.')[-1]}" for nn in correctors]
    if at == mid:
        # Bump 1mm@mid
        targets=[
            xt.TargetSet(x=0, px=0, at=xt.END),
            xt.TargetSet(x=1.485e-3*scale, at=left),
            xt.TargetSet(x=1.485e-3*scale, at=right),
        ]
    else:
        assert at == left or at == right
        at2 = right if at == left else left
        # Bump 1mm@right
        targets=[
            xt.TargetSet(x=0, px=0, at=xt.END),
            xt.TargetSet(x=1.e-3*scale, at=at),
            xt.TargetSet(x=.2e-3*scale, at=at2),
        ]
    opt = line.match(start=correctors[0], end=tw.name[tw.rows.indices[correctors[-1]][0]+20],
                    vary=xt.VaryList(corrector_knobs, step=1.e-7),
                    betx=1, bety=1, x=0, px=0,
                    targets=targets, solve=False)
    opt.solve()
    return opt.actions[0].run(), opt


print('Check bumps')
bump_strengths = {
    'qd.20110':    {13407:1.5589935904933782e-05, 13607:3.5635381547253456e-06, 20207:3.418625982439421e-06, 20407:1.567562976438611e-05},
    'qd.31110':    {30807:1.5590802619432703e-05, 31007:3.5456921731693863e-06, 31207:3.4139073747461334e-06, 31407:1.567463118354537e-05},
    'qd.50110':    {43407:1.5589936379618205e-05, 43607:3.563535125878156e-06, 50207:3.4186259823622525e-06, 50407:1.5675629764448406e-05}
    }

for quad in list(bump_strengths.keys()):
    line = xt.Line.from_json('../../injection_lines/sps_with_aperture_inj_q20_beam_sagitta4.json')
    for nn in bump_strengths[quad]:
        line[f'bump.{nn}'] = bump_strengths[quad][nn]
        line.ref[f'mdh.{nn}'].knl[0] += line.vars[f'bump.{nn}']
    tw = line.twiss()

    print(f'Bump at {quad}:')
    tw.plot('x')
    print(f'  Expected bump strengths: {[bump_strengths[quad][nn] for nn in bump_strengths[quad]]}')
    print(f'  Obtained bump strengths: {[line.vars[f"kmdh{nn}"] for nn in bump_strengths[quad]]}')
    print('')

plt.show()
# print(' ')
# print('Create bump test')
# line = xt.Line.from_json('../../injection_lines/sps_with_aperture_inj_q20_beam_sagitta4.json')
# tw = line.twiss4d()
# tw1, opt1 = create_bump(line, tw, 'qd.31110', ['qf.31010', 'qd.31110', 'qf.31210'])