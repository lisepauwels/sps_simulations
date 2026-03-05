"""
tune_diagram.py
===============
Utilities for plotting accelerator tune diagrams with resonance lines
and sweep trajectories.

Usage example — fractional tunes
---------------------------------
    from tune_diagram import TuneDiagram, SweepTrajectory

    td = TuneDiagram(qx0=0.13, qy0=0.18, half_range=0.35, max_order=3, skew=True)
    fig, ax = td.plot()
    sweep = SweepTrajectory.from_chroma(
        qx0=0.13, qy0=0.18, chromax=20.18, chromay=20.13,
        delta_range=(-4e-3, 4e-3),
    )
    td.finalize(ax, extra_handles=[sweep.plot(ax)])
    plt.show()

Usage example — full tunes
---------------------------
    td = TuneDiagram(qx0=20.13, qy0=20.18, half_range=0.35, max_order=3, skew=True)
    fig, ax = td.plot()
    sweep = SweepTrajectory.from_chroma(
        qx0=20.13, qy0=20.18, chromax=20.18, chromay=20.13,
        delta_range=(-4e-3, 4e-3),
    )
    td.finalize(ax, extra_handles=[sweep.plot(ax)])
    plt.show()
"""

from __future__ import annotations

import warnings
from math import gcd, floor, ceil

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines


# ──────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────────────────────────────────────────

def _gcd3(a: int, b: int, c: int) -> int:
    return gcd(gcd(abs(a), abs(b)), abs(c))


def _line_key(m: int, n: int, p: int) -> tuple:
    """
    Canonical (m, n, p) modulo positive integer scaling and global sign.
    Ensures e.g. (2, 0, 2) and (1, 0, 1) map to the same key.
    """
    g = _gcd3(m, n, p)
    if g == 0:
        return (0, 0, 0)
    m1, n1, p1 = m // g, n // g, p // g
    if (m1 < 0) or (m1 == 0 and n1 < 0) or (m1 == 0 and n1 == 0 and p1 < 0):
        m1, n1, p1 = -m1, -n1, -p1
    return (m1, n1, p1)


def _p_values_in_box(xlim, ylim, m: int, n: int) -> range:
    """All integers p for which m·Qx + n·Qy = p intersects the rectangle."""
    xs = [xlim[0], xlim[1]]
    ys = [ylim[0], ylim[1]]
    vals = [m * x + n * y for x in xs for y in ys]
    return range(floor(min(vals)), ceil(max(vals)) + 1)


def _mn_of_order(order: int) -> list:
    """
    All (m, n) pairs with |m| + |n| == order, NOT reduced to primitive form.

    We keep non-primitive pairs (e.g. (2, 0) at order 2) because they represent
    genuinely different resonance conditions from lower-order lines.
    Duplicate *lines* (same geometry, different scaling) are filtered by _line_key.
    Canonical sign: first nonzero coefficient is positive.
    """
    out: set = set()
    for m in range(-order, order + 1):
        for n in range(-order, order + 1):
            if m == 0 and n == 0:
                continue
            if abs(m) + abs(n) != order:
                continue
            if (m < 0) or (m == 0 and n < 0):
                m, n = -m, -n
            out.add((m, n))
    return sorted(out)


def _draw_line(ax, xlim, ylim, m: int, n: int, p: int, **kw) -> None:
    """Draw m·Qx + n·Qy = p clipped to the plot box."""
    if n == 0:
        ax.vlines(p / m, ylim[0], ylim[1], **kw)
    elif m == 0:
        ax.hlines(p / n, xlim[0], xlim[1], **kw)
    else:
        qx = np.linspace(xlim[0], xlim[1], 300)
        ax.plot(qx, (p - m * qx) / n, **kw)


def _legend_divider(text: str = "─" * 20) -> mlines.Line2D:
    return mlines.Line2D([], [], linestyle="none", color="none", label=text)


def _ordinal_suffix(n: int) -> str:
    return {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th")


# ──────────────────────────────────────────────────────────────────────────────
# Default style tables
# ──────────────────────────────────────────────────────────────────────────────

_DEFAULT_COLORS = {1: "indigo", 2: "blue", 3: "yellowgreen", 4: "darkorange", 5: "red"}
_DEFAULT_ALPHA  = {1: 1.0,     2: 0.85,   3: 0.70,          4: 0.55,        5: 0.45}


# ──────────────────────────────────────────────────────────────────────────────
# TuneDiagram
# ──────────────────────────────────────────────────────────────────────────────

class TuneDiagram:
    """
    Plot resonance lines centred on a working point.

    Works with fractional tunes (e.g. qx0=0.13) or full tunes (e.g. qx0=20.13).

    Parameters
    ----------
    qx0, qy0 : float
        Working-point tunes (fractional or full).
    half_range : float or (float, float)
        Half-width of the displayed window around the working point.
        Single value → equal x/y range; (dx, dy) → asymmetric.
    max_order : int
        Highest resonance order to draw (inclusive).
    skew : bool
        If True, draw skew resonances (m≠0 and n≠0) with a different
        linestyle in addition to normal (m=0 or n=0) resonances.
        If False, draw only normal resonances.
    colors : dict, optional
        Override default {order: color} mapping.
    alpha : dict, optional
        Override default {order: alpha} mapping.
    normal_ls : str
        Linestyle for normal resonances  (default '-').
    skew_ls : str
        Linestyle for skew resonances    (default '--').
    lw : float
        Line width.
    """

    def __init__(
        self,
        qx0: float,
        qy0: float,
        half_range=0.35,
        max_order: int = 3,
        skew: bool = True,
        colors: dict | None = None,
        alpha: dict | None = None,
        normal_ls: str = "-",
        skew_ls: str = "--",
        lw: float = 1.2,
    ):
        self.qx0 = qx0
        self.qy0 = qy0

        if np.isscalar(half_range):
            self.dx = self.dy = float(half_range)
        else:
            self.dx, self.dy = float(half_range[0]), float(half_range[1])

        self.max_order = max_order
        self.skew      = skew
        self.colors    = {**_DEFAULT_COLORS, **(colors or {})}
        self.alpha     = {**_DEFAULT_ALPHA,  **(alpha  or {})}
        self.normal_ls = normal_ls
        self.skew_ls   = skew_ls
        self.lw        = lw

        self.xlim = (qx0 - self.dx, qx0 + self.dx)
        self.ylim = (qy0 - self.dy, qy0 + self.dy)
        self._plotted: set = set()
        self._show_working_point: bool = True  # updated by plot()

    # ------------------------------------------------------------------
    def _draw_family(self, ax, mn_list, color, ls, alpha) -> None:
        for m, n in mn_list:
            for p in _p_values_in_box(self.xlim, self.ylim, m, n):
                key = _line_key(m, n, p)
                if key in self._plotted:
                    continue
                self._plotted.add(key)
                _draw_line(ax, self.xlim, self.ylim, m, n, p,
                           color=color, ls=ls, lw=self.lw, alpha=alpha)

    # ------------------------------------------------------------------
    def plot(
        self,
        ax=None,
        figsize=(8, 7),
        show_working_point: bool = True,
    ):
        """
        Draw resonance lines.

        Parameters
        ----------
        ax : Axes, optional  — existing axes; new figure created if None.
        figsize : tuple      — used only when creating a new figure.
        show_working_point : bool

        Returns
        -------
        fig, ax
        """
        if ax is None:
            fig, ax = plt.subplots(figsize=figsize)
        else:
            fig = ax.get_figure()

        self._plotted.clear()
        self._show_working_point = show_working_point

        for order in range(1, self.max_order + 1):
            color  = self.colors.get(order, "gray")
            alpha  = self.alpha.get(order, 0.6)
            mn_all = _mn_of_order(order)

            mn_normal = [(m, n) for m, n in mn_all if m == 0 or n == 0]
            mn_skew   = [(m, n) for m, n in mn_all if m != 0 and n != 0]

            self._draw_family(ax, mn_normal, color, self.normal_ls, alpha)
            if self.skew:
                self._draw_family(ax, mn_skew, color, self.skew_ls, alpha)

        if show_working_point:
            ax.scatter(self.qx0, self.qy0, color="k", zorder=5, s=40)

        ax.set_xlim(*self.xlim)
        ax.set_ylim(*self.ylim)
        ax.grid(True, alpha=0.4)
        return fig, ax

    # ------------------------------------------------------------------
    def legend_handles(self) -> list:
        """Standard legend handles for the resonance lines."""
        handles = []
        for order in range(1, self.max_order + 1):
            color = self.colors.get(order, "gray")
            suf   = _ordinal_suffix(order)
            handles.append(mlines.Line2D(
                [], [], color=color, ls=self.normal_ls, lw=2,
                label=f"{order}{suf} order",
            ))
        if self._show_working_point:
            handles += [
                _legend_divider(),
                mlines.Line2D([], [], color="k", marker="o", ls="None",
                              markersize=6, label="Working point"),
            ]
        if self.skew:
            handles += [
                _legend_divider(),
                mlines.Line2D([], [], color="k", ls=self.normal_ls, lw=2, label="Normal"),
                mlines.Line2D([], [], color="k", ls=self.skew_ls,   lw=2, label="Skew"),
            ]
        return handles

    # ------------------------------------------------------------------
    def finalize(
        self,
        ax,
        legend_loc: str = "upper left",
        extra_handles: list | None = None,
        xlabel: str | None = None,
        ylabel: str | None = None,
    ) -> None:
        """
        Add legend and axis labels.

        Parameters
        ----------
        ax : Axes
        legend_loc : str
        extra_handles : list, optional
            Additional legend handles inserted at the top
            (e.g. the handle returned by ``sweep.plot(ax)``).
        xlabel, ylabel : str, optional
            Override default axis labels.
        """
        handles = self.legend_handles()
        if extra_handles:
            handles = extra_handles + [_legend_divider()] + handles
        ax.legend(handles=handles, loc=legend_loc, frameon=True)
        ax.set_xlabel(xlabel or r"$Q_x$")
        ax.set_ylabel(ylabel or r"$Q_y$")


# ──────────────────────────────────────────────────────────────────────────────
# SweepTrajectory
# ──────────────────────────────────────────────────────────────────────────────

class SweepTrajectory:
    """
    A momentum-offset sweep shown as a curve on the tune diagram.

    Do not instantiate directly — use :meth:`from_chroma` or
    :meth:`from_twiss_scan`.
    """

    def __init__(self, qx: np.ndarray, qy: np.ndarray):
        self.qx = np.asarray(qx)
        self.qy = np.asarray(qy)

    # ------------------------------------------------------------------
    @classmethod
    def from_chroma(
        cls,
        qx0: float,
        qy0: float,
        chromax: float,
        chromay: float,
        delta_range: tuple = (-5e-3, 5e-3),
        n_points: int = 500,
    ) -> "SweepTrajectory":
        """
        Linear (chromatic) approximation:  Q(δ) = Q₀ + Q′·δ.

        Works identically with fractional or full tunes —
        Q₀ sets the offset, Q′ sets the slope.

        Parameters
        ----------
        qx0, qy0 : float     — working-point tunes (fractional or full)
        chromax, chromay : float  — chromaticities Q′x, Q′y
        delta_range : (δ_min, δ_max)
        n_points : int
        """
        delta = np.linspace(delta_range[0], delta_range[1], n_points)
        return cls(qx0 + chromax * delta, qy0 + chromay * delta)

    # ------------------------------------------------------------------
    @classmethod
    def from_twiss_scan(
        cls,
        line,
        delta_range: tuple = (-7e-3, 7e-3),
        step: float | None = None,
        n_points: int | None = None,
        delta_plot: tuple | None = None,
        use_fractional: bool = False,
        verbose: bool = True,
    ) -> "SweepTrajectory":
        """
        Compute (Qx, Qy) by scanning δ with xsuite ``line.twiss4d``.

        The scan walks away from δ=0 in both directions, using each
        converged closed orbit as the initial guess for the next step.
        Failed twiss points are skipped; a warning is printed if verbose=True.

        Parameters
        ----------
        line : xsuite Line
        delta_range : (δ_min, δ_max)
        step : float, optional    — δ spacing (mutually exclusive with n_points)
        n_points : int, optional  — total number of δ points
        delta_plot : (δ_min, δ_max), optional
            Only keep points in this sub-range (e.g. well-converged region).
        use_fractional : bool
            If True, store qx % 1 and qy % 1.
            If False (default), store full tune values.
        verbose : bool
            Warn on each failed twiss evaluation.

        Returns
        -------
        SweepTrajectory
        """
        deltas = _delta_grid(delta_range, step, n_points)
        results = []   # list of (delta, qx, qy)

        def _extract(tw):
            qx = tw.qx % 1 if use_fractional else tw.qx
            qy = tw.qy % 1 if use_fractional else tw.qy
            return qx, qy

        # reference at δ = 0
        co_ref = None
        try:
            tw0 = line.twiss4d(delta0=0.0)
            qx, qy = _extract(tw0)
            results.append((0.0, qx, qy))
            co_ref = tw0.particle_on_co
        except Exception as exc:
            if verbose:
                warnings.warn(f"twiss4d failed at δ=0: {exc}")

        # negative half: walk 0 → delta_min
        co_prev = co_ref
        for d in deltas[deltas < 0][::-1]:
            try:
                kw = {"co_guess": co_prev} if co_prev is not None else {}
                tw = line.twiss4d(delta0=float(d), **kw)
                qx, qy = _extract(tw)
                results.append((float(d), qx, qy))
                co_prev = tw.particle_on_co
            except Exception as exc:
                if verbose:
                    warnings.warn(f"twiss4d failed at δ={d:.6g}: {exc}")

        # positive half: walk 0 → delta_max
        co_prev = co_ref
        for d in deltas[deltas > 0]:
            try:
                kw = {"co_guess": co_prev} if co_prev is not None else {}
                tw = line.twiss4d(delta0=float(d), **kw)
                qx, qy = _extract(tw)
                results.append((float(d), qx, qy))
                co_prev = tw.particle_on_co
            except Exception as exc:
                if verbose:
                    warnings.warn(f"twiss4d failed at δ={d:.6g}: {exc}")

        if not results:
            raise RuntimeError("All twiss evaluations failed — cannot build trajectory.")

        results.sort(key=lambda t: t[0])
        ds  = np.array([r[0] for r in results])
        qxs = np.array([r[1] for r in results])
        qys = np.array([r[2] for r in results])

        if delta_plot is not None:
            mask = (ds >= delta_plot[0]) & (ds <= delta_plot[1])
            qxs, qys = qxs[mask], qys[mask]

        return cls(qxs, qys)

    # ------------------------------------------------------------------
    def plot(
        self,
        ax,
        color: str = "orangered",
        lw: float = 2.0,
        ls: str = "-",
        label: str = "Sweep trajectory",
        zorder: int = 3,
    ) -> mlines.Line2D:
        """
        Draw the trajectory on *ax*.

        Returns a legend handle — pass it to ``td.finalize(extra_handles=[...])``.
        """
        ax.plot(self.qx, self.qy, color=color, lw=lw, ls=ls, zorder=zorder)
        return mlines.Line2D([], [], color=color, lw=lw, ls=ls, label=label)


# ──────────────────────────────────────────────────────────────────────────────
# Internal delta grid helper
# ──────────────────────────────────────────────────────────────────────────────

def _delta_grid(delta_range, step, n_points) -> np.ndarray:
    if step is None and n_points is None:
        raise ValueError("Provide either 'step' or 'n_points'.")
    dmin, dmax = delta_range
    if step is not None:
        i_min = int(np.ceil(dmin / step))
        i_max = int(np.floor(dmax / step))
        return step * np.arange(i_min, i_max + 1)
    return np.linspace(dmin, dmax, n_points)


# ──────────────────────────────────────────────────────────────────────────────
# Demo  (python tune_diagram.py)
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    fig, axes = plt.subplots(1, 2, figsize=(15, 6))

    # left: fractional tunes
    td1 = TuneDiagram(qx0=0.13, qy0=0.18, half_range=0.35, max_order=3, skew=True)
    td1.plot(ax=axes[0])
    s1 = SweepTrajectory.from_chroma(0.13, 0.18, 20.18, 20.13, delta_range=(-4e-3, 4e-3))
    td1.finalize(axes[0], extra_handles=[s1.plot(axes[0])],
                 xlabel=r"$Q_x$ (fractional)", ylabel=r"$Q_y$ (fractional)")
    axes[0].set_title("Fractional tunes")

    # right: full tunes
    td2 = TuneDiagram(qx0=20.13, qy0=20.18, half_range=0.35, max_order=3, skew=True)
    td2.plot(ax=axes[1])
    s2 = SweepTrajectory.from_chroma(20.13, 20.18, 20.18, 20.13, delta_range=(-4e-3, 4e-3))
    td2.finalize(axes[1], extra_handles=[s2.plot(axes[1])],
                 xlabel=r"$Q_x$", ylabel=r"$Q_y$")
    axes[1].set_title("Full tunes")

    plt.tight_layout()
    plt.show()
