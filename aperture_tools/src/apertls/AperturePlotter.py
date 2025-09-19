import matplotlib.pyplot as plt
import xtrack as xt
#import ApertureCalculator as ac
from .ApertureCalculator import ApertureCalculator
import ipywidgets as widgets
import mplcursors
import matplotlib.patches as patches
import matplotlib.ticker as ticker
import numpy as np

class AperturePlotter:
    def __init__(self, line: xt.Line, aperture_calculator: ApertureCalculator):
        self.line = line
        self.aperture_calculator = aperture_calculator
        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.ax.set_title('Aperture Plot')
        self.ax.set_xlabel('s (m)')
        self.ax.set_ylabel('Aperture (m)')
        self.ax.grid(True)
        self.cursor = mplcursors.cursor(hover=True)
        self.cursor.connect("add", self.on_hover)

    def on_hover(self, sel):
        sel.annotation.set_text(f's: {sel.target[0]:.2f} m\nAperture: {sel.target[1]:.2f} m')