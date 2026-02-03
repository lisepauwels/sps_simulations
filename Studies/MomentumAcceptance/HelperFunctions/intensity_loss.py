import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.lines import Line2D
from matplotlib import colormaps
import os

from plot_helpers import generate_distinct_dashes

def chroma_to_color(cmap, norm, chroma):
    return cmap(norm(chroma))

def plot_intensity_drop(normalised_intensity, line_types=None, chromas=None, line_styles=None, cmap=None, savefig=None):
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    if line_types is None:
        line_types = list(normalised_intensity.keys())
    if chromas is None:
        chromas = list(normalised_intensity[line_types[0]])

    if line_styles is None:
        line_styles = {}
        if len(line_types) <= 4:
            ls_basic = ['-', '--', '-.', ':']
            for i, lt in enumerate(line_types):
                line_styles[lt] = ls_basic[i]
        else:
            styles = generate_distinct_dashes(len(line_types), include_solid=True)
            for i, lt in enumerate(line_types):
                line_styles[lt] = styles[i]
    
    if cmap is None:
        cmap = colormaps['coolwarm']
    
    all_chromas = sorted({ch for lt in normalised_intensity for ch in normalised_intensity[lt].keys()})
    vmin, vmax = min(all_chromas), max(all_chromas)
    norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)

    for lt in line_types:
        for c in chromas:
            for plane in ['DPpos', 'DPneg']:
                ax.plot(
                    normalised_intensity[lt][c][plane]['deltas'],
                    normalised_intensity[lt][c][plane]['values'],
                    color=chroma_to_color(cmap, norm, c),
                    linestyle=line_styles[lt],
                )
    
    line_handles = [
        Line2D([0], [0], color='black', linestyle=line_styles[lt], linewidth=2, label=lt)
        for lt in line_styles
    ]
    legend_model = ax.legend(handles=line_handles, title="Model", loc="upper left", frameon=True)
    ax.add_artist(legend_model)

    sm = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])  # required by older mpl for colorbar
    cbar = fig.colorbar(sm, ax=ax, pad=0.02)
    cbar.set_label("Chromaticity  $Q'_x$")

    ax.set_xlabel(r"$\delta$")
    ax.set_ylabel('Normalised Intensity Loss')
    ax.grid()
    fig.tight_layout()

    if savefig is not None:
        figures_path = os.path.join(os.getcwd(), "Figures")

        if os.path.isdir(figures_path):
            plt.savefig(os.path.join(figures_path, savefig), dpi=300)
        else:
            plt.savefig(savefig, dpi=300)
    
    return fig, ax