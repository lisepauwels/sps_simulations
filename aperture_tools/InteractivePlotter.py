import matplotlib.pyplot as plt
import xtrack as xt
import ApertureCalculator as ac
import ipywidgets as widgets
import mplcursors
import matplotlib.patches as patches
import matplotlib.ticker as ticker
import numpy as np

class InteractiveAperturePlotter:
    def __init__(self, line_thin, line_thick, ap_x = None, ap_y = None, elements = None, thick_elements_colors = None):
        self.line = line_thin
        self.line_thick = line_thick

        #Aperture data
        if ap_x is None or ap_y is None:
            self.ap_calc = ac.ApertureCalculator(line_thin)
            self.x_ext = self.ap_calc.compute_x_extent()
            self.y_ext = self.ap_calc.compute_y_extent()
        else:
            self.x_ext = ap_x
            self.y_ext = ap_y
        
        #Magnet colors
        if thick_elements_colors == None:
            self.thick_elements_colors = {'Bend' :'red',
                        'Quadrupole' :'green',
                        'Sextupole' :'purple',
                        'Octupole' :'brown',
                        'Multipole' :'orange',
                        'Collimator' :'black',
                        'Cavity' :'blue'}
        else:
            self.thick_elements_colors = thick_elements_colors
        
        #Line info for on_click
        self.s_starts, self.s_centers, self.s_ends, self.magnet_names, self.magnet_types = self.get_thick_line_info()
        self.ap_pos, self.ap_names = self.get_thin_line_info()
        
        plt.ion()
        
        self.fig, (self.ax_elements, self.ax_aperture_x, self.ax_aperture_y) = plt.subplots(3, 1, sharex=True, gridspec_kw={'height_ratios': [1, 4, 4]})
        self.ap_pos, self.ap_names = self.get_thin_line_info()
        
        self.setup_plot()
        self.connect_events()
        self.make_legend()
        
        xticks = np.linspace(0, 7000, num=8)
        self.ax_aperture_y.set_xticks(xticks)
        self.ax_aperture_y.set_xticklabels([f"{int(tick)}" for tick in xticks])

    def get_thick_line_info(self):
        tab_thick = self.line_thick.get_table()
        mask_thick = [el in self.thick_elements_colors for el in tab_thick.element_type]
        s_starts = tab_thick.s_start[mask_thick]
        s_centers = tab_thick.s_center[mask_thick]
        s_ends = tab_thick.s_end[mask_thick]
        magnet_names = tab_thick.name[mask_thick]
        magnet_types = tab_thick.element_type[mask_thick]
        return s_starts, s_centers, s_ends, magnet_names, magnet_types
    
    def get_thin_line_info(self):
        tab_thin = self.line.get_table()
        mask_thin = [el.startswith('Limit') for el in tab_thin.element_type]
        s = tab_thin.s[mask_thin]
        names = tab_thin.name[mask_thin]
        return s, names
        
    def setup_plot(self):
        """Initialize the plots."""
        self.ax_aperture_x.set_title("X Aperture")
        self.ax_aperture_y.set_title("Y Aperture")
        self.ax_elements.set_title("Elements")

        
        self.ax_elements.set_ylim(0, 1)
        self.ax_elements.set_yticks([])
        self.ax_elements.set_xticklabels([])
        
        
        self.ax_aperture_x.minorticks_on()
        self.ax_aperture_y.minorticks_on()
        self.ax_aperture_x.set_ylabel("x [m]")
        self.ax_aperture_y.set_ylabel("y [m]")
        self.ax_aperture_y.set_xlabel("s [m]")
        self.ax_aperture_x.grid(visible=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        self.ax_aperture_x.grid(visible=True, which='major', color='#666666', linestyle='-', alpha=0.5)
        self.ax_aperture_y.grid(visible=True, which='minor', color='#999999', linestyle='-', alpha=0.2)
        self.ax_aperture_y.grid(visible=True, which='major', color='#666666', linestyle='-', alpha=0.5)
        
        # Initial plotting
        self.plot_apertures()
        self.plot_elements()
        
        self.ax_aperture_x.format_coord = self.format_coord
        self.ax_aperture_y.format_coord = self.format_coord
        self.ax_elements.format_coord = self.format_coord
        
        self.fig.canvas.draw_idle()

    def plot_apertures(self):
        """Plot aperture data."""
        tab = self.line.get_table()
        mask = [el.startswith('Limit') for el in tab.element_type]
        
        s = tab.s[mask]
        x_min = self.x_ext[:,0]
        x_max = self.x_ext[:,1]
        y_min = self.y_ext[:,0]
        y_max = self.y_ext[:,1]
        
        self.ax_aperture_x.plot(s, x_min, 's-', markersize = 2, label="x_min", color = 'blueviolet')
        self.ax_aperture_x.plot(s, x_max, 's-', markersize = 2, label="x_max", color = 'blueviolet')
        self.ax_aperture_x.legend()
        
        self.ax_aperture_y.plot(s, y_min, 's-', markersize = 2, label="y_min", color = 'blueviolet')
        self.ax_aperture_y.plot(s, y_max, 's-', markersize = 2, label="y_max", color = 'blueviolet')
        self.ax_aperture_y.legend()

    def plot_elements(self):
        """Plot thick elements."""
        
        for i in range(len(self.s_starts)):
            name = self.magnet_names[i]
            s_start = self.s_starts[i]
            s_end = self.s_ends[i]
            element_type = self.magnet_types[i]
            color = self.thick_elements_colors[element_type]
            
            width = s_end - s_start
            rect = patches.Rectangle((s_start, 0.2), width, 0.6, edgecolor=color, facecolor=color, alpha=0.7, label=name)
            self.ax_elements.add_patch(rect)

    
    def get_display_coords(self, ax, x_data, y_data):
        return ax.transData.transform(np.vstack([x_data, y_data]).T)

    def on_click(self, event):
        """Handle click events."""
        if event.xdata is None or event.ydata is None:
            return  # Ignore clicks outside the plot area
        
        if event.inaxes == self.ax_elements:
            click_x = event.xdata
            
            # Remove previous annotations
            for annotation in reversed(self.ax_elements.texts):
                annotation.remove()
            
            # Find the closest magnet
            distances = np.abs(self.s_centers - click_x)
            min_index = np.argmin(distances)
            
            
            sensitivity = 0.5  # Adjust if needed
            
            
            if click_x >= self.s_starts[min_index]-sensitivity and click_x <= self.s_ends[min_index]+sensitivity:
                index = min_index
            
            elif min_index > 0 and click_x >= self.s_starts[min_index-1]-sensitivity and click_x <= self.s_ends[min_index-1]+sensitivity:
                index = min_index-1
            
            elif min_index < len(self.s_centers) - 1 and click_x >= self.s_starts[min_index+1]-sensitivity and click_x <= self.s_ends[min_index+1]+sensitivity:
                index = min_index+1
            
            else:
                return # Ignore clicks outside the magnet area
            
            # Annotate the clicked magnet
            self.ax_elements.annotate(f"{self.magnet_names[index]}\ns = {self.s_centers[index]:.2f} m",
                            xy=(self.s_centers[index], 0.95),
                            xytext=(self.s_centers[index], 0.999),
                            ha="center", fontsize=10, color="black",
                            bbox=dict(facecolor="yellow", edgecolor="black", alpha=0.7),
                            arrowprops=dict(facecolor="black", arrowstyle="->"))
            
            self.fig.canvas.draw_idle()  # Update the figure
        
        elif event.inaxes == self.ax_aperture_x:
            # Convert clicked position to display coordinates
            click_x, click_y = event.x, event.y
            
            for annotation in reversed(self.ax_aperture_x.texts):
                annotation.remove()
                
            # Convert data points to pixel coordinates
            display_coords_max = self.get_display_coords(self.ax_aperture_x, self.ap_pos, self.x_ext[:,1])
            display_coords_min = self.get_display_coords(self.ax_aperture_x, self.ap_pos, self.x_ext[:,0])

            # Stack all points together
            all_coords = np.vstack([display_coords_max, display_coords_min])
            indices = np.hstack([np.arange(len(self.ap_pos)), np.arange(len(self.ap_pos))])  # Keep track of which index it belongs to
            dataset_labels = np.hstack(["max"] * len(self.ap_pos) + ["min"] * len(self.ap_pos))  # Label the source (max or min)

            # Find closest point in pixel coordinates
            distances = np.sqrt((all_coords[:, 0] - click_x) ** 2 + (all_coords[:, 1] - click_y) ** 2)
            min_index = np.argmin(distances)
            
            # Define a sensitivity threshold (in pixels)
            sensitivity = 10  # Adjust if needed

            if distances[min_index] < sensitivity:
                # Remove previous annotations
                for annotation in reversed(self.ax_aperture_x.texts):
                    annotation.remove()

                # Get current zoom level
                x_range = self.ax_aperture_x.get_xlim()
                y_range = self.ax_aperture_x.get_ylim()
                
                # Calculate adaptive offsets based on zoom level
                x_offset = (x_range[1] - x_range[0]) * 0.02  # 2% of x-axis range
                y_offset = (y_range[1] - y_range[0]) * 0.02  # 2% of y-axis range

                # Determine whether it's from x_max or x_min
                original_index = indices[min_index]
                dataset = dataset_labels[min_index]
                y_value = self.x_ext[:,1][original_index] if dataset == "max" else self.x_ext[:,0][original_index]

                # Annotate the closest point
                self.ax_aperture_x.annotate(f"{self.ap_names[original_index]} ({dataset})\n(s={self.ap_pos[original_index]:.2f}, x={y_value:.2f})",
                            xy=(self.ap_pos[original_index], y_value),
                            xytext=(self.ap_pos[original_index] + x_offset, y_value + y_offset),
                            bbox=dict(facecolor='yellow', edgecolor='black', alpha=0.7),
                            arrowprops=dict(facecolor='black', arrowstyle="->"))
                self.fig.canvas.draw_idle()
                
        elif event.inaxes == self.ax_aperture_y:
            click_x, click_y = event.x, event.y
            
            for annotation in reversed(self.ax_aperture_y.texts):
                annotation.remove()
                
            # Convert data points to pixel coordinates
            display_coords_max = self.get_display_coords(self.ax_aperture_y, self.ap_pos, self.y_ext[:,1])
            display_coords_min = self.get_display_coords(self.ax_aperture_y, self.ap_pos, self.y_ext[:,0])

            # Stack all points together
            all_coords = np.vstack([display_coords_max, display_coords_min])
            indices = np.hstack([np.arange(len(self.ap_pos)), np.arange(len(self.ap_pos))])  # Keep track of which index it belongs to
            dataset_labels = np.hstack(["max"] * len(self.ap_pos) + ["min"] * len(self.ap_pos))  # Label the source (max or min)

            # Find closest point in pixel coordinates
            distances = np.sqrt((all_coords[:, 0] - click_x) ** 2 + (all_coords[:, 1] - click_y) ** 2)
            min_index = np.argmin(distances)
            
            # Define a sensitivity threshold (in pixels)
            sensitivity = 10  # Adjust if needed

            if distances[min_index] < sensitivity:
                # Remove previous annotations
                for annotation in reversed(self.ax_aperture_y.texts):
                    annotation.remove()

                # Get current zoom level
                x_range = self.ax_aperture_y.get_xlim()
                y_range = self.ax_aperture_y.get_ylim()
                
                # Calculate adaptive offsets based on zoom level
                x_offset = (x_range[1] - x_range[0]) * 0.02  # 2% of x-axis range
                y_offset = (y_range[1] - y_range[0]) * 0.02  # 2% of y-axis range

                # Determine whether it's from x_max or x_min
                original_index = indices[min_index]
                dataset = dataset_labels[min_index]
                y_value = self.y_ext[:,1][original_index] if dataset == "max" else self.y_ext[:,0][original_index]

                # Annotate the closest point
                self.ax_aperture_y.annotate(f"{self.ap_names[original_index]} ({dataset})\n(s={self.ap_pos[original_index]:.2f}, x={y_value:.2f})",
                            xy=(self.ap_pos[original_index], y_value),
                            xytext=(self.ap_pos[original_index] + x_offset, y_value + y_offset),
                            bbox=dict(facecolor='yellow', edgecolor='black', alpha=0.7),
                            arrowprops=dict(facecolor='black', arrowstyle="->"))
                self.fig.canvas.draw_idle()

    def update_xticks(self, event):
        x_min, x_max = event.get_xlim()
        
        # Use MaxNLocator to find reasonable tick positions (e.g., multiples of 10, 50, etc.)
        locator = ticker.MaxNLocator(nbins=10, integer=True, prune="both")  # Adjust nbins if needed
        xticks = locator.tick_values(x_min, x_max)

        # Update ticks and labels
        self.ax_aperture_x.set_xticks(xticks)
        self.ax_aperture_x.set_xticklabels([f"{tick:.0f}" for tick in xticks])
        self.ax_aperture_y.set_xticks(xticks)
        self.ax_aperture_y.set_xticklabels([f"{tick:.0f}" for tick in xticks])
        
    def on_zoom(self, event):
        # Temporarily disable callback to prevent recursion
        self.ax_aperture_x.callbacks.disconnect(self.on_zoom.cid)
        self.ax_aperture_y.callbacks.disconnect(self.on_zoom.cid)
        x_min, x_max = self.ax_aperture_x.get_xlim()
        self.ax_elements.set_xlim(x_min, x_max)
        
        self.update_xticks(event)
        # Reconnect callback
        self.on_zoom.cid = self.ax_aperture_x.callbacks.connect('xlim_changed', self.on_zoom)
        self.on_zoom.cid = self.ax_aperture_y.callbacks.connect('xlim_changed', self.on_zoom)

        self.fig.canvas.draw_idle()

    def connect_events(self):
        """Connect interactive event handlers."""
        self.fig.canvas.mpl_connect("button_press_event", self.on_click)
        self.fig.canvas.mpl_connect("scroll_event", self.on_zoom)
        
    def make_legend(self):
        """Create a legend."""
        legend_patches = [patches.Patch(color=color, label=element) for element, color in self.thick_elements_colors.items()]
        self.ax_elements.legend(handles=legend_patches, loc="upper left", bbox_to_anchor=(1, 1), title="Magnet Types", fontsize=10)
        self.fig.subplots_adjust(right=0.8)
    
    def format_coord(self, x, y):
        return f"s = {x:.2f}, x = {y:.2f}"

    def show(self):
        """Display the plot."""
        plt.show()
    
    def plot_5sigma_beam(self, exn=3.5e-6, nrj=21, pmass=0.938):
        tw = self.line.twiss()
        self.ax_aperture_x.plot(tw.s, 5*np.sqrt(tw.betx*exn*pmass/nrj), color='royalblue', label='5 sigma')
        self.ax_aperture_x.plot(tw.s, -5*np.sqrt(tw.betx*exn*pmass/nrj), color='royalblue')
        self.ax_aperture_y.plot(tw.s, 5*np.sqrt(tw.bety*exn*pmass/nrj), color='royalblue', label='5 sigma')
        self.ax_aperture_y.plot(tw.s, -5*np.sqrt(tw.bety*exn*pmass/nrj), color='royalblue')
        self.ax_aperture_x.legend()
        self.ax_aperture_y.legend()
        self.fig.canvas.draw_idle()
    
    def plot_5sigma_off_momentum(self, exn=3.5e-6, nrj=21, pmass=0.938, bucket_height=3.4e-3):
        tw = self.line.twiss()
        self.ax_aperture_x.plot(tw.s, 5*np.sqrt(tw.betx*exn*pmass/nrj)+bucket_height*tw.dx, color='darkgreen', label='5 sigma + 1 bucket D_x')
        self.ax_aperture_x.plot(tw.s, -5*np.sqrt(tw.betx*exn*pmass/nrj)-bucket_height*tw.dx, color='darkgreen')
        self.ax_aperture_y.plot(tw.s, 5*np.sqrt(tw.bety*exn*pmass/nrj)+bucket_height*tw.dy, color='darkgreen', label='5 sigma + 1 bucket D_y')
        self.ax_aperture_y.plot(tw.s, -5*np.sqrt(tw.bety*exn*pmass/nrj)-bucket_height*tw.dy, color='darkgreen')
        self.ax_aperture_x.legend()
        self.ax_aperture_y.legend()
    
    def plot_dispersion(self, exn=3.5e-6, nrj=21, pmass=0.938, bucket_height=3.4e-3):
        tw = self.line.twiss()
        coll_id = list(tw.name).index('tcsm.51932')
        self.ax_aperture_x.plot(tw.s, 0.02*np.sin(2*np.pi*((tw.mux-tw.mux[coll_id]) % 1)), color='orange', label='mux wrt collimator')
        self.ax_aperture_y.plot(tw.s, 0.02*np.sin(2*np.pi*((tw.muy-tw.muy[coll_id]) % 1)), color='orange', label='muy wrt collimator')
        self.ax_aperture_x.legend()
        self.ax_aperture_y.legend()