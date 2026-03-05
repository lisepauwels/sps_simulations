import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from pathlib import Path

# ── helpers (copied from plot.py) ────────────────────────────────────────────

def dr_to_delta(dR):
    dR = np.asarray(dR, dtype=float) / 1000
    sps_radius = 1100.
    sps_gtr    = 17.95
    return dR / sps_radius * sps_gtr * sps_gtr


def _pick_cmap(n):
    """Return (cmap, imod) for n locations."""
    if n > 10:
        return mpl.colormaps['tab20'], 20
    return mpl.colormaps['tab10'], 10


def _filter_locations(locations, *dicts):
    """
    Keep only locations that are present in at least one of the provided dicts.
    Comparison is case-insensitive; the returned list uses the capitalised form.
    """
    kept = []
    for loc in locations:
        loc_up  = loc.upper()
        loc_low = loc.lower()
        in_any  = any(
            loc_up in d or loc_low in d or
            f"{loc_up}_POS" in d or f"{loc_up}_NEG" in d
            for d in dicts
        )
        if in_any:
            kept.append(loc_up)
        else:
            print(f"Warning: {loc_up} not found in any provided dataset.")
    return kept


# ── data extractors ───────────────────────────────────────────────────────────

def _sim_xy(sim_midpoints, loc):
    """
    Extract (bumps, deltas) arrays from simulation midpoints for one location.
    sim_midpoints[loc.lower()]['DPneg' | 'DPpos'] = {bump: delta_1e-3}
    Returns list of (x_array, y_array) — one per DP direction present.
    """
    entry = sim_midpoints.get(loc.lower(), {})
    curves = []
    for key, sign in [('DPneg', -1), ('DPpos', 1)]:
        if key not in entry:
            continue
        data = entry[key]
        bumps  = np.array(list(data.keys()),   dtype=float)
        deltas = sign * np.array(list(data.values()), dtype=float)
        order  = np.argsort(bumps)
        curves.append((bumps[order], deltas[order]))
    return curves


def _md_xy(md_midpoints, loc, correct_bump_fn=None):
    """
    Extract (bumps, deltas) arrays from MD midpoints for one location.
    md_midpoints[loc | loc_POS | loc_NEG][bump] = [list of radial-steering values in mm]
    Returns list of (x_mean_array, y_mean_array) — one per suffix present.
    """
    curves = []
    for suffix, sign in [('_POS', 1), ('_NEG', -1), ('', 1)]:
        key = loc + suffix if suffix else loc
        if key not in md_midpoints:
            continue
        mid = md_midpoints[key]
        bumps, deltas = [], []
        for bump_key, vals in mid.items():
            b = correct_bump_fn(key, float(bump_key)) if correct_bump_fn else float(bump_key)
            d = sign * 1000 * dr_to_delta(np.mean(vals))
            bumps.append(b)
            deltas.append(d)
        order = np.argsort(bumps)
        bumps  = np.array(bumps)[order]
        deltas = np.array(deltas)[order]
        curves.append((bumps, deltas))
    return curves


# ── main plotting function ────────────────────────────────────────────────────

def plot_midpoints_comparison(
    sim_midpoints,
    md_midpoints      = None,
    locations         = None,
    correct_bump_fn   = None,
    name              = None,
    xlim              = None,
    ylim              = None,
    figsize           = (9, 15/4),
    legend            = 'upper center',
    md_alpha          = 0.4,
    sim_linestyle     = '-',
    md_linestyle      = '--',
    save              = True,
    ax                = None,
):
    """
    Plot simulation midpoints (solid lines) and optionally overlay MD midpoints
    (same colour, lower alpha) for a list of locations.

    Parameters
    ----------
    sim_midpoints : dict
        {loc_lowercase: {'DPneg': {bump: delta_1e-3}, 'DPpos': {bump: delta_1e-3}}}
    md_midpoints : dict, optional
        {loc_UPPERCASE[_POS|_NEG]: {bump: [list of R values in mm]}}
    locations : list of str, optional
        Locations to plot (case-insensitive). Defaults to all keys in sim_midpoints.
    correct_bump_fn : callable, optional
        plot.correct_bump — applies bump correction to MD data. Pass None to skip.
    name : str, optional
        Suffix for the saved filename.
    xlim, ylim : tuple, optional
        Axis limits.
    figsize : tuple
        Figure size.
    legend : str or None
        Legend location string, or None to skip legend.
    md_alpha : float
        Alpha for MD curves (0–1).
    save : bool
        Whether to save the figure.
    ax : matplotlib Axes, optional
        Plot into an existing axes instead of creating a new figure.

    Returns
    -------
    fig, ax
    """
    # ── resolve locations ────────────────────────────────────────────────────
    all_dicts = [d for d in (sim_midpoints, md_midpoints) if d is not None]
    if locations is None:
        locations = [k.upper() for k in sim_midpoints.keys()]
    else:
        locations = _filter_locations(locations, *all_dicts)

    locations = [loc for loc in locations if not loc.startswith('REFERENCE')]

    cmap, imod = _pick_cmap(len(locations))

    # ── set up axes ──────────────────────────────────────────────────────────
    own_fig = ax is None
    if own_fig:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.get_figure()

    # ── plot ─────────────────────────────────────────────────────────────────
    for i, loc in enumerate(locations):
        color = cmap(i % imod)

        # simulation curves
        for j, (x, y) in enumerate(_sim_xy(sim_midpoints, loc)):
            label = loc if j == 0 else '_nolegend_'
            ax.plot(x, y, 'o' + sim_linestyle, color=color, label=label)

        # MD overlay
        if md_midpoints is not None:
            for x, y in _md_xy(md_midpoints, loc, correct_bump_fn):
                ax.plot(x, y, 'o' + md_linestyle, color=color, alpha=md_alpha)

    from matplotlib.lines import Line2D
    extra_handles = [
        Line2D([0], [0], color='k', linestyle=md_linestyle,   label='Measured'),
        Line2D([0], [0], color='k', linestyle=sim_linestyle,  label='Simulated'),
    ]

    # ── formatting ───────────────────────────────────────────────────────────
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    ax.minorticks_on()
    # ax.grid(which='both')
    ax.grid(visible=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
    ax.grid(visible=True, which='major', color='#666666', linestyle='-', alpha=0.5)
    ax.set_xlabel("Bump [mm]")
    ax.set_ylabel(r"$\delta\; [10^{-3}]$")
    ax.set_title("Off-momentum shift needed to scrape 50% intensity")
    if legend:
        handles, labels = ax.get_legend_handles_labels()
        if md_midpoints is not None:
            extra_handles = [
                Line2D([0], [0], color='k', linestyle=sim_linestyle, label='Simulated'),
                Line2D([0], [0], color='k', linestyle=md_linestyle,  label='Measured'),
            ]
            handles += extra_handles
            labels  += ['Simulated', 'Measured']
        ax.legend(handles=handles, labels=labels, loc=legend)

    # ── save ─────────────────────────────────────────────────────────────────
    if save and own_fig:
        out_name = f"delta_vs_bump_{name}.png" if name else "delta_vs_bump_comparison.png"
        out_name2 = f"delta_vs_bump_{name}.pdf" if name else "delta_vs_bump_comparison.pdf"
        out_path = Path.cwd() / "plots" / out_name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path, dpi=300, bbox_inches='tight')
        out_path2 = Path.cwd() / "plots" / out_name2
        fig.savefig(out_path2, dpi=300, bbox_inches='tight')

    if own_fig:
        plt.close(fig)

    return fig, ax
