import numpy as np
import matplotlib.pyplot as plt
import plot_helpers as ph
import os
from itertools import product

def get_measurements_combinations(deltas_plus, deltas_min):
    return list(product(deltas_plus, deltas_min))

def df_to_delta(df):
    slip_factor = 0.0017935055033301713
    f = 200_000_000
    return 1/slip_factor * df/f

def interpolate_percentile_val(xvals, yvals, percentile=0.5):
    if np.any(yvals <= percentile):  # ensure the curve actually crosses percentile
        idx_above = np.where(yvals > percentile)[0][-1]   # last index above percentile
        idx_below = idx_above + 1                  # first index below percentile

        # Linear interpolation for more accuracy
        x50 = np.interp(percentile, [yvals[idx_above], yvals[idx_below]],
                            [xvals[idx_above], xvals[idx_below]])
        return x50
    else:
        print("Warning: The curve does not cross percentile")
        return None

def get_midpoints(normalised_intensity, percentile=0.5,sim_data=True):
    intensity_midpoints = {}
    if sim_data:
        for lt in normalised_intensity:
            intensity_midpoints[lt] = {}
            for c in normalised_intensity[lt]:
                intensity_midpoints[lt][c] = {}
                for plane in normalised_intensity[lt][c]:
                    deltas = normalised_intensity[lt][c][plane]['deltas']
                    values = normalised_intensity[lt][c][plane]['values']

                    x50 = interpolate_percentile_val(deltas, values, percentile=percentile)
                    intensity_midpoints[lt][c][plane] = x50
    else:
        pass
    return intensity_midpoints

def restructure_md_midpoints(md_midpoints_old):
    md_midpoints = {}
    for chroma_val in md_midpoints_old[list(md_midpoints_old.keys())[0]]:
        chroma = float(chroma_val.split('_')[-1])
        md_midpoints[chroma] = {}

    for sign in md_midpoints_old:
        if sign == 'pos':
            plane = 'DPpos'
        elif sign == 'neg':
            plane = 'DPneg'
        else:
            print('Unvalid sign !')
            AssertionError
        for chroma_val in md_midpoints_old[sign]:
            chroma = float(chroma_val.split('_')[-1])
            md_midpoints[chroma][plane] = md_midpoints_old[sign][chroma_val]
    
    return md_midpoints


def plot_midpoints(midpoints, midpoints_md=None, line_types=None, planes=None, chromas=None, colours=None, line_styles=None, markers=None, is_reversed=True, ylim=None, savefig=None):
    fig, ax = plt.subplots(figsize=(8,6))

    if line_types is None:
        line_types = list(midpoints.keys())

    if planes is None:
        planes = ['DPpos', 'DPneg']

    if chromas is None:
        chromas = sorted(next(iter(midpoints.values())).keys())

    if colours is None:
        if midpoints_md is not None:
            colours_list = ph.random_distinct_colors(len(line_types) + 1)
        else:
            colours_list = ph.random_distinct_colors(len(line_types))
        colours = {line_type: colours_list[i] for i, line_type in enumerate(line_types)}
        colours['MD'] = colours_list[-1]
    
    if line_styles is None:
        styles = ph.generate_distinct_dashes(len(planes))
        line_styles = {plane: styles[i] for i, plane in enumerate(planes)}

    if midpoints_md is not None and markers is None:
        markers = {'DPpos' : 'o', 'DPneg' : 's'} # Hardcoded for now

    for line_type in line_types:
        for plane in planes:
            if plane == 'DPneg' and is_reversed:
                sign = -1
            else:
                sign = 1
            if line_type == 'linear': label = f'No errors - {plane}'
            else: label = f'{line_type} - {plane}'
            ax.plot(chromas, 
                    [sign * midpoints[line_type][chroma][plane] for chroma in chromas],
                    label=label,
                    color=colours[line_type],
                    linestyle=line_styles[plane],
                    marker=markers[plane] if markers is not None else '.', markersize=5)
    if midpoints_md is not None:
        chromas_md = sorted(midpoints_md.keys())
        for chroma in chromas_md:
            for plane in planes:
                if plane == 'DPneg' and is_reversed:
                    sign = -1
                else:
                    sign = 1
                
                y = sign * np.asarray(midpoints_md[chroma][plane])
                x = np.full_like(y, chroma, dtype=float)
                ax.scatter(x, y,
                           label=f'MD - {plane}' if chroma == chromas_md[0] else None,
                           color=colours['MD'],
                           marker=markers[plane],
                           s=12,
                           zorder=5)
    if ylim is not None:
        ax.set_ylim(ylim)
    ax.set_xlabel(r"Normalised Chromaticity $\xi$", fontsize=12)
    ax.set_ylabel(r"$|\delta|$", fontsize=12)
    ax.grid()
    ax.legend(ncols=2 if len(planes) > 1 else 1, fontsize=12, frameon=True)
    ax.set_title(f"Midpoints vs Chromaticity -- {planes[0] if len(planes) == 1 else 'Both Planes'}", fontsize=14)
    plt.tight_layout()
    plt.show()

    if savefig is not None:
        figures_path = os.path.join(os.getcwd(), "Figures")

        if os.path.isdir(figures_path):
            fig.savefig(os.path.join(figures_path, savefig), dpi=300)
        else:
            fig.savefig(savefig, dpi=300)
    
    return fig, ax