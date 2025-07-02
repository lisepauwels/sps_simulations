import xtrack as xt
import numpy as np
# import matplotlib
# matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import apertls

env = xt.load_madx_lattice('sps.seq')
env.vars.load_madx('lhc_q20.str')
line = env.sps

line_ap = xt.Line.from_json('../../injection_lines/sps_with_aperture_inj_q20_beam_sagitta2.json')
line_ap_calc = apertls.ApertureCalculator(line_ap)
x_extent = line_ap_calc.compute_x_extent()

x_min = x_extent[:,0]
x_max = x_extent[:,1]

tt = line_ap.get_table()
mask = np.array([line_ap[elem].__class__.__name__.startswith('Limit') for elem in tt.name[:-1]])
s = tt.s[:-1][mask]

line.particle_ref = xt.Particles(energy0=26e9)
env.particle_ref = line.particle_ref

tw = line.twiss4d()
tw_offmom = line.twiss4d(delta0=-7.35e-3)

band_pos = tw_offmom.x + 5*np.sqrt(2e-6/28*tw_offmom.betx)
band_neg = tw_offmom.x - 5*np.sqrt(2e-6/28*tw_offmom.betx)

fig, ax = plt.subplots(figsize=(6,3))
# ax.hlines(-4.15e-2, 0, 7000, color='r', ls='--', label='QD aperture')
# ax.hlines(-7.8e-2, 0, 7000, color='g', ls='--', label='QF aperture')
ax.plot(s, x_min, color='tab:orange', ls = '--', label='Element apertures')
ax.plot(s, x_max, color='tab:orange', ls = '--')
ax.fill_between(tw_offmom.s, band_neg, band_pos, where=(band_pos > band_neg), interpolate=True, color='tab:blue', alpha=0.3)
ax.plot(tw_offmom.s, tw_offmom.x, label=r'Closed orbit for $\delta_0=-7.35\cdot 10^{-3}$')
ax.plot(tw_offmom.rows['qd.*'].s, tw_offmom.rows['qd.*'].x, 'r.', label='QD')
ax.plot(tw_offmom.rows['qf.*'].s, tw_offmom.rows['qf.*'].x, 'g.', label='QF')
ax.plot(tw_offmom.rows['qd.11110'].s, tw_offmom.rows['qd.11110'].x, 'kx', label='QD.11110')
ax.set_xlabel('s [m]')
ax.set_ylabel('x [m]')
ax.legend(loc='upper right')
fig.tight_layout()
plt.show()