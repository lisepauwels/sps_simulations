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
from scipy.interpolate import CubicSpline


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
# TuneMap
# ──────────────────────────────────────────────────────────────────────────────

class TuneMap:
    """
    Continuous mapping  δ → (Qx, Qy)  built from a :class:`SweepTrajectory`.

    Internally uses cubic-spline interpolation, so queries are smooth and
    accurate for any δ within the trajectory's delta range.

    Obtain via :meth:`SweepTrajectory.build_map` — do not instantiate directly.

    Parameters
    ----------
    delta : array_like
        Momentum offsets (sorted, ascending) from the trajectory.
    qx, qy : array_like
        Corresponding tune values.

    Attributes
    ----------
    delta_min, delta_max : float
        Valid interpolation range.

    Examples
    --------
    >>> sweep = SweepTrajectory.from_chroma(0.13, 0.18, 20.18, 20.13,
    ...                                     delta_range=(-4e-3, 4e-3))
    >>> tm = sweep.build_map()
    >>> qx, qy = tm(1.5e-3)           # scalar query
    >>> qx, qy = tm(np.linspace(-3e-3, 3e-3, 200))  # array query
    >>> delta   = tm.invert_qx(0.145) # find δ for a given Qx
    """

    def __init__(self, delta: np.ndarray, qx: np.ndarray, qy: np.ndarray):
        order = np.argsort(delta)
        self._delta = delta[order]
        self._qx    = qx[order]
        self._qy    = qy[order]

        self.delta_min = float(self._delta[0])
        self.delta_max = float(self._delta[-1])

        self._cs_qx = CubicSpline(self._delta, self._qx)
        self._cs_qy = CubicSpline(self._delta, self._qy)

    # ------------------------------------------------------------------
    def __call__(
        self,
        delta,
        extrapolate: bool = False,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Evaluate the map at one or more δ values.

        Parameters
        ----------
        delta : float or array_like
            Momentum offset(s) at which to query.
        extrapolate : bool
            If False (default), values outside [delta_min, delta_max] raise
            a ValueError.  If True, the spline is extrapolated (use with care).

        Returns
        -------
        qx, qy : ndarray (or float if scalar input)
            Interpolated tunes.
        """
        scalar = np.isscalar(delta)
        d = np.atleast_1d(np.asarray(delta, dtype=float))

        if not extrapolate:
            oob = (d < self.delta_min) | (d > self.delta_max)
            if oob.any():
                raise ValueError(
                    f"δ values {d[oob]} are outside the map range "
                    f"[{self.delta_min:.4g}, {self.delta_max:.4g}]. "
                    "Pass extrapolate=True to allow extrapolation."
                )

        qx = self._cs_qx(d)
        qy = self._cs_qy(d)

        if scalar:
            return float(qx[0]), float(qy[0])
        return qx, qy

    # ------------------------------------------------------------------
    def invert_qx(self, target_qx: float, extrapolate: bool = False) -> np.ndarray:
        """
        Find all δ values where Qx(δ) = *target_qx*.

        Uses a fine grid search followed by Brent-method root-finding for
        each sign change, so it handles non-monotone trajectories correctly.

        Parameters
        ----------
        target_qx : float
        extrapolate : bool
            Passed through to :meth:`__call__` for bounds checking.

        Returns
        -------
        deltas : ndarray
            All δ roots found (may be empty if target is outside the range).
        """
        return self._invert(self._cs_qx, target_qx, extrapolate)

    # ------------------------------------------------------------------
    def invert_qy(self, target_qy: float, extrapolate: bool = False) -> np.ndarray:
        """
        Find all δ values where Qy(δ) = *target_qy*.

        See :meth:`invert_qx` for details.
        """
        return self._invert(self._cs_qy, target_qy, extrapolate)

    # ------------------------------------------------------------------
    def _invert(self, cs, target, extrapolate):
        from scipy.optimize import brentq

        d_fine = np.linspace(self.delta_min, self.delta_max, 2000)
        residual = cs(d_fine) - target
        roots = []
        for i in range(len(residual) - 1):
            if residual[i] * residual[i + 1] < 0:
                try:
                    r = brentq(lambda d: cs(d) - target, d_fine[i], d_fine[i + 1])
                    roots.append(r)
                except ValueError:
                    pass
        return np.array(roots)

    # ------------------------------------------------------------------
    def sample(self, n: int = 500) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Return (delta, qx, qy) arrays uniformly sampled over the full range.

        Useful for tabulating the map or for further analysis.

        Parameters
        ----------
        n : int
            Number of sample points.

        Returns
        -------
        delta, qx, qy : ndarray
        """
        d = np.linspace(self.delta_min, self.delta_max, n)
        qx = self._cs_qx(d)
        qy = self._cs_qy(d)
        return d, qx, qy

    # ------------------------------------------------------------------
    def plot_map(
        self,
        n: int = 500,
        fig=None,
        color_qx: str = "steelblue",
        color_qy: str = "tomato",
        delta_unit: float = 1e-3,
        delta_unit_label: str = r"$10^{-3}$",
    ):
        """
        Plot Qx(δ) and Qy(δ) as functions of δ on a shared x-axis.

        Parameters
        ----------
        n : int
            Sampling resolution.
        fig : Figure, optional
            Existing figure; a new one is created if None.
        color_qx, color_qy : str
        delta_unit : float
            Divide δ axis by this factor (default 1e-3 → display in units of 10⁻³).
        delta_unit_label : str
            Label suffix for the δ axis.

        Returns
        -------
        fig, (ax_qx, ax_qy)
        """
        d, qx, qy = self.sample(n)
        d_plot = d / delta_unit

        if fig is None:
            fig, (ax_qx, ax_qy) = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
        else:
            ax_qx, ax_qy = fig.axes[:2]

        ax_qx.plot(d_plot, qx, color=color_qx, lw=2)
        ax_qx.set_ylabel(r"$Q_x$")
        ax_qx.grid(True, alpha=0.4)

        ax_qy.plot(d_plot, qy, color=color_qy, lw=2)
        ax_qy.set_ylabel(r"$Q_y$")
        ax_qy.set_xlabel(rf"$\delta$ [{delta_unit_label}]")
        ax_qy.grid(True, alpha=0.4)

        fig.tight_layout()
        return fig, (ax_qx, ax_qy)

    # ------------------------------------------------------------------
    def save(self, path: str) -> None:
        """
        Save the map to a ``.npz`` file.

        Only the three raw arrays (delta, qx, qy) are stored — the splines
        are cheap to rebuild on load.

        Parameters
        ----------
        path : str
            File path.  A ``.npz`` extension is appended automatically if absent.

        Examples
        --------
        >>> tm.save("tune_map_qx20.13.npz")
        >>> tm2 = TuneMap.load("tune_map_qx20.13.npz")
        """
        np.savez(path, delta=self._delta, qx=self._qx, qy=self._qy)

    # ------------------------------------------------------------------
    @classmethod
    def load(cls, path: str) -> "TuneMap":
        """
        Load a :class:`TuneMap` previously saved with :meth:`save`.

        Parameters
        ----------
        path : str
            Path to the ``.npz`` file.

        Returns
        -------
        TuneMap

        Examples
        --------
        >>> tm = TuneMap.load("tune_map_qx20.13.npz")
        >>> qx, qy = tm(1.5e-3)
        """
        data = np.load(path)
        return cls(data["delta"], data["qx"], data["qy"])

    # ------------------------------------------------------------------
    def __repr__(self) -> str:
        return (
            f"TuneMap(delta=[{self.delta_min:.4g}, {self.delta_max:.4g}], "
            f"n_nodes={len(self._delta)})"
        )


# ──────────────────────────────────────────────────────────────────────────────
# SweepTrajectory
# ──────────────────────────────────────────────────────────────────────────────

class SweepTrajectory:
    """
    A momentum-offset sweep shown as a curve on the tune diagram.

    Do not instantiate directly — use :meth:`from_chroma` or
    :meth:`from_twiss_scan`.
    """

    def __init__(self, qx: np.ndarray, qy: np.ndarray, delta: np.ndarray | None = None):
        self.qx    = np.asarray(qx)
        self.qy    = np.asarray(qy)
        self.delta = np.asarray(delta) if delta is not None else None

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
        return cls(qx0 + chromax * delta, qy0 + chromay * delta, delta=delta)

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
            ds, qxs, qys = ds[mask], qxs[mask], qys[mask]

        return cls(qxs, qys, delta=ds)

    # ------------------------------------------------------------------
    @staticmethod
    def find_delta_limit(
        line,
        sign: int,
        tt_aper,
        max_delta_scan: float = 1e-2,
        n_scan_points: int = 100,
        verbose: bool = False,
    ) -> float:
        """
        Find the maximum |δ| before the closed orbit hits the aperture.

        Walks away from δ=0 in the direction given by *sign* (+1 or -1),
        stopping as soon as the horizontal closed orbit reaches the aperture
        boundary (x_aper_high for positive δ, x_aper_low for negative δ).

        Parameters
        ----------
        line : xsuite Line
        sign : int
            +1 for positive δ scan, -1 for negative δ scan.
        tt_aper : table
            Aperture table with columns x_aper_high and x_aper_low.
        max_delta_scan : float
            Maximum |δ| to scan up to (default 1e-2).
        n_scan_points : int
            Number of steps in the scan (default 100).
        verbose : bool
            Print progress and result (default False).

        Returns
        -------
        float
            The first δ at which the closed orbit reaches the aperture,
            or sign * max_delta_scan if the aperture is never reached.

        Examples
        --------
        >>> delta_pos = SweepTrajectory.find_delta_limit(line, +1, tt_aper)
        >>> delta_neg = SweepTrajectory.find_delta_limit(line, -1, tt_aper)
        >>> sweep = SweepTrajectory.from_twiss_scan(
        ...     line, delta_range=(delta_neg, delta_pos), n_points=100
        ... )
        """
        if sign not in (+1, -1):
            raise ValueError("sign must be +1 or -1.")

        if sign == +1:
            clearance = lambda tw: np.min(tt_aper.x_aper_high - tw.x)
            hit        = lambda d: d <= 0
        else:
            clearance = lambda tw: np.max(tt_aper.x_aper_low - tw.x)
            hit        = lambda d: d >= 0

        delta_range = np.linspace(0, sign * max_delta_scan, n_scan_points)
        tw_prev     = line.twiss4d()
        delta_limit = sign * max_delta_scan  # fallback if aperture never reached

        for delta in delta_range[1:]:
            try:
                tw = line.twiss4d(delta0=delta, co_guess=tw_prev.particle_on_co)
            except Exception:
                if verbose:
                    warnings.warn(f"twiss4d failed at δ={delta:.4g}, skipping.")
                continue

            d = clearance(tw)
            if verbose:
                print(f"  δ={delta:+.4g}  clearance={d:.4g}")

            if hit(d):
                delta_limit = delta
                if verbose:
                    print(f"Aperture reached at δ={delta:+.4g} (clearance={d:.4g})")
                break

            tw_prev = tw  # only update on success

        return delta_limit

    # ------------------------------------------------------------------
    def build_map(self) -> "TuneMap":
        """
        Build a continuous :class:`TuneMap` from this trajectory.

        The map provides smooth cubic-spline interpolation of Qx(δ) and
        Qy(δ) for any δ within the trajectory's delta range, plus
        convenience methods for inverse lookup and tabular sampling.

        Returns
        -------
        TuneMap

        Raises
        ------
        ValueError
            If the trajectory has no associated delta array.

        Examples
        --------
        >>> sweep = SweepTrajectory.from_chroma(0.13, 0.18, 20.18, 20.13,
        ...                                     delta_range=(-4e-3, 4e-3))
        >>> tm = sweep.build_map()
        >>> qx, qy = tm(1.5e-3)          # scalar
        >>> qx, qy = tm(np.linspace(-3e-3, 3e-3, 200))  # array
        >>> delta   = tm.invert_qx(0.145)  # inverse lookup
        >>> tm.plot_map()                  # visualise Qx(δ), Qy(δ)
        """
        if self.delta is None:
            raise ValueError(
                "This SweepTrajectory has no associated delta array. "
                "Use from_chroma() or from_twiss_scan() to obtain one."
            )
        return TuneMap(self.delta, self.qx, self.qy)

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
    import tempfile, os

    # ══════════════════════════════════════════════════════════════════════
    # Example 1 — Fractional tunes vs full tunes
    # ══════════════════════════════════════════════════════════════════════
    #
    # The TuneDiagram and SweepTrajectory work identically in both
    # conventions, but the two must be consistent with each other:
    #   • fractional  → qx0 ∈ [0, 1),  trajectory built with qx0 ∈ [0, 1)
    #   • full        → qx0 = integer + fraction, trajectory matches
    #
    # The resonance lines are the same geometry either way; only the
    # axis labels and the numeric values on the ticks differ.

    QX0_FRAC, QY0_FRAC = 0.13, 0.18       # fractional working point
    QX0_FULL, QY0_FULL = 20.13, 20.18     # full working point
    CHROMA_X, CHROMA_Y = 5.0, 5.0
    DELTA_RANGE        = (-4e-3, 4e-3)

    fig1, axes1 = plt.subplots(1, 2, figsize=(15, 6))
    fig1.suptitle("Example 1 — Fractional vs full tunes", fontsize=13)

    # --- left: fractional tunes -------------------------------------------
    td_frac = TuneDiagram(qx0=QX0_FRAC, qy0=QY0_FRAC,
                          half_range=0.35, max_order=3, skew=True)
    td_frac.plot(ax=axes1[0], show_working_point=True)

    sweep_frac = SweepTrajectory.from_chroma(
        QX0_FRAC, QY0_FRAC, CHROMA_X, CHROMA_Y, delta_range=DELTA_RANGE
    )
    td_frac.finalize(
        axes1[0],
        extra_handles=[sweep_frac.plot(axes1[0])],
        xlabel=r"$Q_x$ (fractional)",
        ylabel=r"$Q_y$ (fractional)",
    )
    axes1[0].set_title("Fractional tunes")

    # --- right: full tunes ------------------------------------------------
    td_full = TuneDiagram(qx0=QX0_FULL, qy0=QY0_FULL,
                          half_range=0.35, max_order=3, skew=True)
    td_full.plot(ax=axes1[1], show_working_point=True)

    sweep_full = SweepTrajectory.from_chroma(
        QX0_FULL, QY0_FULL, CHROMA_X, CHROMA_Y, delta_range=DELTA_RANGE
    )
    td_full.finalize(
        axes1[1],
        extra_handles=[sweep_full.plot(axes1[1])],
        xlabel=r"$Q_x$",
        ylabel=r"$Q_y$",
    )
    axes1[1].set_title("Full tunes")

    fig1.tight_layout()

    # ══════════════════════════════════════════════════════════════════════
    # Example 2 — Find aperture limits, build sweep, save map, reload, query
    # ══════════════════════════════════════════════════════════════════════
    #
    # Real workflow with xsuite:
    #   1. Find δ limits  →  SweepTrajectory.find_delta_limit(line, ±1, tt_aper)
    #   2. Build trajectory  →  SweepTrajectory.from_twiss_scan(line, delta_range)
    #   3. Build map         →  sweep.build_map()
    #   4. Save map          →  tm.save(path)
    #   5. Load map later    →  TuneMap.load(path)
    #   6. Query             →  tm(delta) / tm.sample(n)
    #
    # Here we mock the xsuite objects so the demo runs without xsuite.
    # Replace the mock section with real line/tt_aper in your workflow.

    print("\n" + "═" * 60)
    print("Example 2 — aperture limits, build, save, reload, query")
    print("═" * 60)

    # ── Mock xsuite line and aperture table (replace with real objects) ──
    class _MockParticle:
        pass

    class _MockTwiss:
        """Minimal twiss-like object for the demo."""
        def __init__(self, delta0, qx0, qy0, chroma_x, chroma_y, aper_half=2e-2):
            n = 100
            self.qx = qx0 + chroma_x * delta0
            self.qy = qy0 + chroma_y * delta0
            # closed orbit x: linear dispersion (D=2 m, typical)
            self.x  = np.full(n, 2.0 * delta0)
            self.particle_on_co = _MockParticle()

    class _MockLine:
        """Minimal xsuite Line stand-in."""
        def __init__(self, qx0, qy0, chroma_x, chroma_y):
            self._qx0, self._qy0 = qx0, qy0
            self._cx,  self._cy  = chroma_x, chroma_y

        def twiss4d(self, delta0=0.0, co_guess=None):
            # Simulate aperture loss at |δ| > 7e-3
            if abs(delta0) > 7e-3:
                raise RuntimeError(f"Closed orbit lost at δ={delta0:.4g}")
            return _MockTwiss(delta0, self._qx0, self._qy0, self._cx, self._cy)

    class _MockAper:
        """Minimal aperture table stand-in (100 elements, half-gap = 15 mm)."""
        def __init__(self, half_gap=15e-3):
            self.x_aper_high =  np.full(100, half_gap)
            self.x_aper_low  = -np.full(100, half_gap)

    mock_line  = _MockLine(QX0_FULL, QY0_FULL, CHROMA_X, CHROMA_Y)
    mock_aper  = _MockAper(half_gap=15e-3)   # ±15 mm aperture, D=2 m → limit ~7.5e-3
    # ── End of mock section ─────────────────────────────────────────────

    # 1. Find aperture-limited δ range
    print("\nStep 1 — find aperture limits:")
    delta_pos = SweepTrajectory.find_delta_limit(
        mock_line, +1, mock_aper, max_delta_scan=1e-2, n_scan_points=100, verbose=True,
    )
    delta_neg = SweepTrajectory.find_delta_limit(
        mock_line, -1, mock_aper, max_delta_scan=1e-2, n_scan_points=100, verbose=True,
    )
    print(f"  → δ range: [{delta_neg:.4g}, {delta_pos:.4g}]")

    # 2. Build trajectory over the aperture-limited range
    print("\nStep 2 — build trajectory:")
    sweep2 = SweepTrajectory.from_chroma(
        QX0_FULL, QY0_FULL, CHROMA_X, CHROMA_Y,
        delta_range=(delta_neg, delta_pos), n_points=300,
    )
    # With a real line, use instead:
    # sweep2 = SweepTrajectory.from_twiss_scan(
    #     mock_line, delta_range=(delta_neg, delta_pos), n_points=300,
    # )
    print(f"  → trajectory: {len(sweep2.delta)} points over "
          f"[{sweep2.delta.min():.4g}, {sweep2.delta.max():.4g}]")

    # 3. Build map
    print("\nStep 3 — build map:")
    tm = sweep2.build_map()
    print(f"  → {tm}")

    # 4. Save / 5. Reload
    print("\nStep 4 & 5 — save and reload:")
    with tempfile.TemporaryDirectory() as tmpdir:
        map_path = os.path.join(tmpdir, "tune_map_Qx20.13_Qy20.18.npz")
        tm.save(map_path)
        print(f"  → saved:    {map_path}")
        tm2 = TuneMap.load(map_path)
        print(f"  → reloaded: {tm2}")

    # 6. Query the reloaded map
    print("\nStep 6 — query:")
    qx0_check, qy0_check = tm2(0.0)
    print(f"  At δ=0       → Qx={qx0_check:.6f}  Qy={qy0_check:.6f}")
    print(f"  Working point  → Qx={QX0_FULL:.6f}  Qy={QY0_FULL:.6f}")

    print("\n  Sample over ±3×10⁻³:")
    d_sample = np.linspace(-3e-3, 3e-3, 7)
    qx_s, qy_s = tm2(d_sample)
    for d, qx, qy in zip(d_sample, qx_s, qy_s):
        print(f"    δ={d:+.4f}   Qx={qx:.6f}   Qy={qy:.6f}")

    roots = tm2.invert_qx(QX0_FULL + CHROMA_X * 2e-3)
    print(f"\n  invert_qx({QX0_FULL + CHROMA_X * 2e-3:.5f}) → δ={roots}")

    # Also show the Qx(δ), Qy(δ) map plot
    fig2, _ = tm2.plot_map(delta_unit=1e-3, delta_unit_label=r"$10^{-3}$")
    fig2.suptitle("Example 2 — Qx(δ) and Qy(δ) from reloaded map", fontsize=13)

    # ══════════════════════════════════════════════════════════════════════
    # Example 3 — Plot colour-coded trajectory on a tighter tune diagram
    # ══════════════════════════════════════════════════════════════════════
    #
    # The TuneMap gives us back the (δ, Qx, Qy) arrays via tm.sample(),
    # which we then feed into a LineCollection so each segment is coloured
    # by its δ value.  The TuneDiagram here uses a smaller half_range to
    # zoom in around the working point.

    from matplotlib.collections import LineCollection
    import matplotlib.lines as mlines

    fig3, ax3 = plt.subplots(figsize=(9, 8))
    fig3.suptitle("Example 3 — Colour-coded trajectory on zoomed tune diagram",
                  fontsize=13)

    td_zoom = TuneDiagram(qx0=QX0_FULL, qy0=QY0_FULL,
                          half_range=0.15, max_order=3, skew=True)
    td_zoom.plot(ax=ax3, show_working_point=True)

    # Sample the map — use the full saved range but plot only within the
    # diagram window (points outside are simply clipped by the axes limits)
    d_arr, qx_arr, qy_arr = tm2.sample(500)

    points   = np.array([qx_arr, qy_arr]).T.reshape(-1, 1, 2)
    segments = np.concatenate([points[:-1], points[1:]], axis=1)

    norm = plt.Normalize(d_arr.min(), d_arr.max())
    lc   = LineCollection(segments, cmap="coolwarm", norm=norm, lw=2.5, zorder=3)
    lc.set_array(0.5 * (d_arr[:-1] + d_arr[1:]))  # midpoint δ per segment
    ax3.add_collection(lc)

    cbar = fig3.colorbar(lc, ax=ax3, label=r"$\delta\ [10^{-3}]$", pad=0.02)
    cbar.set_ticks(np.linspace(d_arr.min(), d_arr.max(), 9))
    cbar.set_ticklabels([f"{v * 1e3:.1f}" for v in cbar.get_ticks()])

    # Mark δ = 0 explicitly
    qx_at0, qy_at0 = tm2(0.0)
    ax3.scatter(qx_at0, qy_at0, color="k", zorder=6, s=60,
                label=r"$\delta = 0$")

    # Proxy handle for the trajectory in the legend
    traj_handle = mlines.Line2D([], [], color="orangered", lw=2.5,
                                label="Sweep trajectory")
    delta0_handle = mlines.Line2D([], [], marker="o", color="k", ls="None",
                                  markersize=7, label=r"$\delta = 0$")

    td_zoom.finalize(ax3, extra_handles=[traj_handle, delta0_handle])
    fig3.tight_layout()

    plt.show()