import numpy as np
import matplotlib.pyplot as plt
import os
from midpoints_analysis import get_measurements_combinations
from plot_helpers import random_distinct_colors

def get_acceptance(delta_plus, delta_min):
    return delta_plus - delta_min

def get_center(delta_plus, delta_min):
    return 0.5 * (delta_plus + delta_min)


# -----------------------
# Shared helpers (pure)
# -----------------------

def _default_line_types(intensity_midpoints):
    return list(intensity_midpoints.keys())

def _default_chromas(intensity_midpoints, line_types):
    lt0 = line_types[0]
    return sorted(intensity_midpoints[lt0].keys())

def _validate_md_structure(md_midpoints):
    if md_midpoints is None:
        return
    first_key = next(iter(md_midpoints.keys()))
    if first_key in ("pos", "neg"):
        raise ValueError(
            "md_midpoints has wrong structure (starts with 'pos'/'neg'). "
            "Apply restructure_md_midpoints first."
        )

def _make_default_style(line_types, md_midpoints, colours=None, markers=None):
    if colours is None:
        colours = {}
        n = len(line_types) + (2 if md_midpoints is not None else 0)
        colour_list = random_distinct_colors(n)
        for i, lt in enumerate(line_types):
            colours[lt] = colour_list[i]
        if md_midpoints is not None:
            colours["MD_means"] = colour_list[-2]
            colours["MD_stds"]  = colour_list[-1]

    if markers is None:
        markers = {lt: "o" for lt in line_types}
        if md_midpoints is not None:
            markers["MD_data"]  = "s"
            markers["MD_means"] = "o"

    return colours, markers


# -----------------------
# Center-specific helpers
# -----------------------

def _centers_vs_chroma_for_line(intensity_midpoints, line_type, chromas=None):
    by_chroma = intensity_midpoints[line_type]
    chroma_list = sorted(by_chroma.keys()) if chromas is None else sorted(chromas)

    xs, ys = [], []
    for c in chroma_list:
        if c not in by_chroma:
            continue
        dp = by_chroma[c]
        ys.append(get_center(dp.get("DPpos", np.nan), dp.get("DPneg", np.nan)))
        xs.append(float(c))

    return np.asarray(xs, float), np.asarray(ys, float)

def _md_centers_from_combinations(md_midpoints):
    centers_md = {}
    xs_all, ys_all = [], []

    for c, d in md_midpoints.items():
        combos = get_measurements_combinations(d["DPpos"], d["DPneg"])
        pts = np.array([get_center(plus, minus) for (plus, minus) in combos], dtype=float)

        centers_md[c] = {
            "points": pts,
            "mean": float(np.mean(pts)) if pts.size else np.nan,
            "std": float(np.std(pts, ddof=0)) if pts.size else np.nan,
        }

        if pts.size:
            xs_all.append(np.full(pts.shape, float(c)))
            ys_all.append(pts)

    xs = np.concatenate(xs_all) if xs_all else np.array([], dtype=float)
    ys = np.concatenate(ys_all) if ys_all else np.array([], dtype=float)
    return centers_md, xs, ys


# ---------------------------
# Acceptance-specific helpers
# ---------------------------

def _acceptance_vs_chroma_for_line(intensity_midpoints, line_type, chromas=None):
    """
    acceptance = delta_plus - delta_minus
    Expects delta_minus possibly negative already; the formula matches your definition.
    """
    by_chroma = intensity_midpoints[line_type]
    chroma_list = sorted(by_chroma.keys()) if chromas is None else sorted(chromas)

    xs, ys = [], []
    for c in chroma_list:
        if c not in by_chroma:
            continue
        dp = by_chroma[c]
        ys.append(get_acceptance(dp.get("DPpos", np.nan), dp.get("DPneg", np.nan)))
        xs.append(float(c))

    return np.asarray(xs, float), np.asarray(ys, float)

def _md_acceptance_from_combinations(md_midpoints):
    """
    Build acceptance points from all DPpos x DPneg combinations per chroma.
    acceptance = delta_plus - delta_minus
    """
    acc_md = {}
    xs_all, ys_all = [], []

    for c, d in md_midpoints.items():
        combos = get_measurements_combinations(d["DPpos"], d["DPneg"])
        pts = np.array([get_acceptance(plus, minus) for (plus, minus) in combos], dtype=float)

        acc_md[c] = {
            "points": pts,
            "mean": float(np.mean(pts)) if pts.size else np.nan,
            "std": float(np.std(pts, ddof=0)) if pts.size else np.nan,
        }

        if pts.size:
            xs_all.append(np.full(pts.shape, float(c)))
            ys_all.append(pts)

    xs = np.concatenate(xs_all) if xs_all else np.array([], dtype=float)
    ys = np.concatenate(ys_all) if ys_all else np.array([], dtype=float)
    return acc_md, xs, ys


# -----------------------
# Main plot functions
# -----------------------

def plot_centers(
    intensity_midpoints,
    *,
    line_types=None,
    chromas=None,
    colours=None,
    markers=None,
    md_midpoints=None,
    md_point_color="k",
    md_point_size=6,
    md_point_alpha=0.7,
    band_alpha=0.25,
    savefig=None
):
    _validate_md_structure(md_midpoints)

    if line_types is None:
        line_types = _default_line_types(intensity_midpoints)
    if chromas is None:
        chromas = _default_chromas(intensity_midpoints, line_types)

    colours, markers = _make_default_style(line_types, md_midpoints, colours, markers)

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    for lt in line_types:
        x, y = _centers_vs_chroma_for_line(intensity_midpoints, lt, chromas=chromas)
        ax.plot(
            x, y,
            color=colours.get(lt, None),
            marker=markers.get(lt, "o"),
            linestyle="-",
            label=str(lt),
            zorder=3,
        )

    if md_midpoints is not None:
        centers_md, xs, ys = _md_centers_from_combinations(md_midpoints)

        ax.scatter(
            xs, ys,
            color=md_point_color,
            marker=markers.get("MD_data", "s"),
            s=md_point_size,
            alpha=md_point_alpha,
            label="MD samples",
            zorder=2,
        )

        md_chromas = np.array(sorted(centers_md.keys()), dtype=float)
        md_means = np.array([centers_md[c]["mean"] for c in md_chromas], dtype=float)
        md_stds  = np.array([centers_md[c]["std"]  for c in md_chromas], dtype=float)

        ax.plot(
            md_chromas, md_means,
            color=colours["MD_means"],
            marker=markers.get("MD_means", "o"),
            linestyle="-",
            label="MD mean",
            zorder=4,
        )

        ax.fill_between(
            md_chromas,
            md_means - md_stds,
            md_means + md_stds,
            color=colours["MD_stds"],
            alpha=band_alpha,
            label=r"MD $\pm 1\sigma$",
            zorder=1,
            linewidth=0,
        )

    ax.grid(alpha=0.3)
    ax.set_xlabel(r"Chromaticity $Q'_x$")
    ax.set_ylabel(r"Center $C = (\delta_+ + \delta_-)/2$")
    ax.legend(title="Model", fontsize=9)
    fig.tight_layout()

    if savefig is not None:
        figures_path = os.path.join(os.getcwd(), "Figures")

        if os.path.isdir(figures_path):
            plt.savefig(os.path.join(figures_path, savefig), dpi=300)
        else:
            plt.savefig(savefig, dpi=300)
    return fig, ax


def plot_acceptance(
    intensity_midpoints,
    *,
    line_types=None,
    chromas=None,
    colours=None,
    markers=None,
    md_midpoints=None,
    md_point_color="k",
    md_point_size=6,
    md_point_alpha=0.7,
    band_alpha=0.25,
    savefig=None
):
    """
    Same plotting style as plot_centers, but for:
      acceptance = delta_plus - delta_minus
    """
    _validate_md_structure(md_midpoints)

    if line_types is None:
        line_types = _default_line_types(intensity_midpoints)
    if chromas is None:
        chromas = _default_chromas(intensity_midpoints, line_types)

    colours, markers = _make_default_style(line_types, md_midpoints, colours, markers)

    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    # ---- Simulation/model curves ----
    for lt in line_types:
        x, y = _acceptance_vs_chroma_for_line(intensity_midpoints, lt, chromas=chromas)
        ax.plot(
            x, y,
            color=colours.get(lt, None),
            marker=markers.get(lt, "o"),
            linestyle="-",
            label=str(lt),
            zorder=3,
        )

    # ---- MD overlay ----
    if md_midpoints is not None:
        acc_md, xs, ys = _md_acceptance_from_combinations(md_midpoints)

        ax.scatter(
            xs, ys,
            color=md_point_color,
            marker=markers.get("MD_data", "s"),
            s=md_point_size,
            alpha=md_point_alpha,
            label="MD samples",
            zorder=2,
        )

        md_chromas = np.array(sorted(acc_md.keys()), dtype=float)
        md_means = np.array([acc_md[c]["mean"] for c in md_chromas], dtype=float)
        md_stds  = np.array([acc_md[c]["std"]  for c in md_chromas], dtype=float)

        ax.plot(
            md_chromas, md_means,
            color=colours["MD_means"],
            marker=markers.get("MD_means", "o"),
            linestyle="-",
            label="MD mean",
            zorder=4,
        )

        ax.fill_between(
            md_chromas,
            md_means - md_stds,
            md_means + md_stds,
            color=colours["MD_stds"],
            alpha=band_alpha,
            label=r"MD $\pm 1\sigma$",
            zorder=1,
            linewidth=0,
        )

    ax.grid(alpha=0.3)
    ax.set_xlabel(r"Chromaticity $Q'_x$")
    ax.set_ylabel(r"Acceptance $A = \delta_+ - \delta_-$")
    ax.legend(title="Model", fontsize=9)
    fig.tight_layout()

    if savefig is not None:
        figures_path = os.path.join(os.getcwd(), "Figures")

        if os.path.isdir(figures_path):
            plt.savefig(os.path.join(figures_path, savefig), dpi=300)
        else:
            plt.savefig(savefig, dpi=300)
    return fig, ax