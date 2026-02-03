import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
import xtrack as xt

line = xt.Line.from_json('sps_q20_inj.json')

def compute_betx(x_vals, Nsigma, nemitt_x, line=line):
    amplitude = (np.max(x_vals) - np.min(x_vals))/2
    return (amplitude / Nsigma)**2 / nemitt_x * line.particle_ref.beta0 * line.particle_ref.gamma0

def plot_betx_vs_delta(
    betx_dict,
    *,
    cmap="plasma",
    exclude_sigma_zero=True,
    marker="o",
    linestyle="-",
    figsize=(8, 6),
    savepath=None,
    dpi=300,
):
    """
    Plot βx(δ) for different σ values.

    Parameters
    ----------
    betx_dict : dict
        Dictionary with keys (sigma, delta) -> betx

    cmap : str or Colormap, optional
        Matplotlib colormap name or object

    exclude_sigma_zero : bool, optional
        Remove σ = 0 curve

    marker : str
        Marker style for points

    linestyle : str
        Line style

    figsize : tuple
        Figure size

    savepath : str or None
        If provided, saves figure to this path

    dpi : int
        DPI used when saving

    Returns
    -------
    fig, ax
    """

    # --------------------------
    # Group by sigma
    # --------------------------
    by_sigma = defaultdict(list)
    for (sigma, delta), bx in betx_dict.items():
        by_sigma[sigma].append((delta, bx))

    sigmas = np.array(sorted(by_sigma.keys()))

    if exclude_sigma_zero:
        sigmas = sigmas[~np.isclose(sigmas, 0.0)]

    if len(sigmas) == 0:
        raise ValueError("No sigma values to plot.")

    # --------------------------
    # Colormap handling
    # --------------------------
    cmap = plt.get_cmap(cmap)
    norm = plt.Normalize(sigmas.min(), sigmas.max())

    # --------------------------
    # Figure
    # --------------------------
    fig, ax = plt.subplots(figsize=figsize)

    for sigma in sigmas:
        pairs = sorted(by_sigma[sigma], key=lambda t: t[0])

        deltas = np.array([d for d, _ in pairs])
        betx_vals = np.array([b for _, b in pairs])

        ax.plot(
            deltas,
            betx_vals,
            marker=marker,
            linestyle=linestyle,
            color=cmap(norm(sigma)),
        )

    # --------------------------
    # Labels
    # --------------------------
    ax.set_xlabel(r"$\delta$")
    ax.set_ylabel(r"$\beta_x(\delta)$")

    ax.grid(True, alpha=0.3)

    # --------------------------
    # Colorbar
    # --------------------------
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])

    cbar = fig.colorbar(sm, ax=ax)
    cbar.set_label(r"$\sigma$")

    # --------------------------
    # Save
    # --------------------------
    fig.tight_layout()

    if savepath is not None:
        fig.savefig(savepath, dpi=dpi)
        print(f"Saved figure to {savepath}")

    return fig, ax

def plot_betx_map(
    betx_dict,
    *,
    cmap="plasma",
    exclude_sigma_zero=True,
    marker="o",
    linestyle="-",          # kept for signature compatibility; not used in scatter map
    figsize=(8, 6),
    savepath=None,
    dpi=300,
    s=35,                   # marker size
    edgecolors="none",      # set to "k" if you want marker edges
):
    """
    Plot βx as a colormap on the (δ, σ) plane.

    x-axis: δ
    y-axis: σ
    color:  βx

    Parameters
    ----------
    betx_dict : dict
        Dictionary with keys (sigma, delta) -> betx

    cmap : str or Colormap
        Matplotlib colormap name or object (default: "plasma")

    exclude_sigma_zero : bool
        If True, remove σ = 0 points (default: True)

    marker : str
        Marker used for points (default: "o")

    linestyle : str
        Present for API compatibility; not used in scatter map.

    figsize : tuple
        Figure size (default: (8, 6))

    savepath : str or None
        If provided, saves the figure (default: None)

    dpi : int
        DPI used when saving (default: 300)

    s : float
        Scatter marker size

    edgecolors : str
        Scatter edgecolors (default: "none")

    Returns
    -------
    fig, ax
    """

    # ---- unpack dict into arrays ----
    sigmas = []
    deltas = []
    betx_vals = []

    for (sigma, delta), bx in betx_dict.items():
        if exclude_sigma_zero and np.isclose(sigma, 0.0):
            continue
        sigmas.append(sigma)
        deltas.append(delta)
        betx_vals.append(bx)

    if len(sigmas) == 0:
        raise ValueError("No points to plot (check exclude_sigma_zero and input dict).")

    sigmas = np.asarray(sigmas, dtype=float)
    deltas = np.asarray(deltas, dtype=float)
    betx_vals = np.asarray(betx_vals, dtype=float)

    # ---- figure ----
    fig, ax = plt.subplots(figsize=figsize)

    sc = ax.scatter(
        deltas,
        sigmas,
        c=betx_vals,
        cmap=plt.get_cmap(cmap),
        marker=marker,
        s=s,
        edgecolors=edgecolors,
    )

    # ---- labels ----
    ax.set_xlabel(r"$\delta$")
    ax.set_ylabel(r"$\sigma$")

    # ---- colorbar ----
    cbar = fig.colorbar(sc, ax=ax)
    cbar.set_label(r"$\beta_x$")

    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    # ---- save ----
    if savepath is not None:
        fig.savefig(savepath, dpi=dpi)
        print(f"Saved figure to {savepath}")

    return fig, ax
