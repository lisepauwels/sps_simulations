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
line_thick = xt.Line.from_json('../../injection_lines/injection_thick_approx_ap.json')

plotter = apertls.InteractiveAperturePlotter(line_ap, line_thick)

line.particle_ref = xt.Particles(energy0=26e9)
env.particle_ref = line.particle_ref

tw = line.twiss4d()
tw_offmom = line.twiss4d(delta0=-7.35e-3)

band_pos = tw_offmom.x + 5*np.sqrt(2e-6/28*tw_offmom.betx)
band_neg = tw_offmom.x - 5*np.sqrt(2e-6/28*tw_offmom.betx)

plotter.ax_aperture_x.fill_between(tw_offmom.s, band_neg, band_pos, where=(band_pos > band_neg), interpolate=True, color='tab:blue', alpha=0.3)
plotter.ax_aperture_x.plot(tw_offmom.s, tw_offmom.x, label=r'Closed orbit for $\delta_0=-7.35\cdot 10^{-3}$')
plotter.ax_aperture_x.plot(tw_offmom.rows['qd.*'].s, tw_offmom.rows['qd.*'].x, 'r.', label='QD')
plotter.ax_aperture_x.plot(tw_offmom.rows['qf.*'].s, tw_offmom.rows['qf.*'].x, 'g.', label='QF')
plotter.ax_aperture_x.plot(tw_offmom.rows['qd.11110'].s, tw_offmom.rows['qd.11110'].x, 'kx', label='QD.11110')
# plotter.ax_aperture_x.set_xlabel('s [m]')
# plotter.ax_aperture_x.set_ylabel('x [m]')
# plotter.ax_aperture_x.legend(loc='upper right')
# plotter.fig.tight_layout()
plotter.show()
