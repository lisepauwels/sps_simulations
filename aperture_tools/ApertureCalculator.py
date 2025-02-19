import numpy as np
import xtrack as xt
from abc import ABC, abstractmethod

class ApertureElement(ABC):
    """Abstract base class for aperture elements."""
    
    def __init__(self, element: xt.Limit):
        self.element = element
    
    @abstractmethod
    def compute_x_extent(self):
        """Compute the x extent of the aperture."""
        pass

    @abstractmethod
    def compute_y_extent(self):
        """Compute the y extent of the aperture."""
        pass

class EllipticalAperture(ApertureElement):
    def __init__(self, element: xt.LimitEllipse, name: str):
        super().__init__(element)  # Calls ApertureElement's __init__
        self.name = name
    
    def compute_x_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            return -self.element.a + self.element.shift_x, self.element.a + self.element.shift_x
        
        else:
            t_max = np.arctan(-self.element.b/self.element.a * self.element._sin_rot_s/self.element._cos_rot_s)
            ext = self.element.a*np.cos(t_max)*self.element._cos_rot_s-self.element.b*np.sin(t_max)*self.element._sin_rot_s
            
            if ext < 0: 
                print('ERROR: ellipse extent is negatif')
                
            return -np.abs(ext) + self.shift_x, np.abs(ext) + self.shift_x
        
    def compute_y_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            return -self.element.b + self.element.shift_y, self.element.b + self.element.shift_y
        
        else:
            t_max = np.arctan(self.element.b/self.element.a * self.element._cos_rot_s/self.element._sin_rot_s)
            ext = self.element.a*np.cos(t_max)*self.element._sin_rot_s + self.element.b*np.sin(t_max)*self.element._cos_rot_s
            
            if ext < 0: 
                print('ERROR: ellipse extent is negatif')
                
            return -np.abs(ext) + self.element.shift_y, np.abs(ext) + self.element.shift_y

class RectangularAperture(ApertureElement):
    def __init__(self, element: xt.LimitRect, name: str):
        super().__init__(element)  # Calls ApertureElement's __init__
        self.name = name
    
    def compute_x_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            return self.element.min_x+ self.element.shift_x, self.element.max_x + self.element.shift_x
        else:
            w, h = self.element.max_x-self.element.min_x, self.element.max_y-self.element.min_y
            corners = np.array([[-w/2, -h/2],
                                [w/2, -h/2],
                                [w/2, h/2],
                                [-w/2, h/2]])
            
            rotation_matrix = np.array([
                [self.element._cos_rot_s, -self.element._sin_rot_s],
                [self.element._sin_rot_s,  self.element._cos_rot_s]
            ])
            
            rotated_corners = corners @ rotation_matrix.T
            
            min_x_val = np.min(rotated_corners[:,0])
            max_x_val = np.max(rotated_corners[:,0])
            
            return min_x_val + self.element.shift_x, max_x_val + self.element.shift_x
    
    def compute_y_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            return self.element.min_y+ self.element.shift_y, self.element.max_y + self.element.shift_y
        else:
            w, h = self.element.max_x-self.element.min_x, self.element.max_y-self.element.min_y
            corners = np.array([[-w/2, -h/2],
                                [w/2, -h/2],
                                [w/2, h/2],
                                [-w/2, h/2]])
            
            rotation_matrix = np.array([
                [self.element._cos_rot_s, -self.element._sin_rot_s],
                [self.element._sin_rot_s,  self.element._cos_rot_s]
            ])
            
            rotated_corners = corners @ rotation_matrix.T
            
            min_y_val = np.min(rotated_corners[:,1])
            max_y_val = np.max(rotated_corners[:,1])
            
            return min_y_val + self.element.shift_y, max_y_val + self.element.shift_y

class RectEllipseAperture(ApertureElement):
    def __init__(self, element: xt.LimitRectEllipse, name: str):
        super().__init__(element)
        self.name = name
    
    def compute_x_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            ext = np.min([self.element.a, self.element.max_x])
            
            if ext < 0: 
                print('ERROR: ellipse extent is negatif')
            
            return -np.abs(ext) + self.element.shift_x, np.abs(ext) + self.element.shift_x
        
        else:
            #ellipse part
            t_max = np.arctan(-self.element.b/self.element.a * self.element._sin_rot_s/self.element._cos_rot_s)
            ext_ellipse = np.abs(self.element.a*np.cos(t_max)*self.element._cos_rot_s-self.element.b*np.sin(t_max)*self.element._sin_rot_s)
            
            #rectangle part
            corners = np.array([[-self.element.max_x, -self.element.max_y],
                                [self.element.max_x, -self.element.max_y],
                                [self.element.max_x, self.element.max_y],
                                [-self.element.max_x, self.element.max_y]])
        
            rotation_matrix = np.array([
                [self.element._cos_rot_s, -self.element._sin_rot_s],
                [self.element._sin_rot_s,  self.element._cos_rot_s]
            ])
            
            rotated_corners = corners @ rotation_matrix.T
            ext_rect = np.max(rotated_corners[:,0])
            if ext_rect < 0:
                print("ERROR: rectangle extent from rectellipse is negatif")
            
            ext = np.min([ext_ellipse, ext_rect])
            if ext < 0:
                print("ERROR: extent from rectellipse is negatif")
            
            return -np.abs(ext) + self.element.shift_x, np.abs(ext) + self.element.shift_x
        
    def compute_y_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            ext = np.min([self.element.b, self.element.max_y])
            
            if ext < 0: 
                print('ERROR: ellipse extent is negatif')
            
            return -np.abs(ext) + self.element.shift_y, np.abs(ext) + self.element.shift_y
        
        else:
            #ellipse part
            t_max = np.arctan(self.element.b/self.element.a * self.element._cos_rot_s/self.element._sin_rot_s)
            ext_ellipse = self.element.a*np.cos(t_max)*self.element._sin_rot_s + self.element.b*np.sin(t_max)*self.element._cos_rot_s
            
            #rectangle part
            corners = np.array([[-self.element.max_x, -self.element.max_y],
                                [self.element.max_x, -self.element.max_y],
                                [self.element.max_x, self.element.max_y],
                                [-self.element.max_x, self.element.max_y]])
            
            rotation_matrix = np.array([
                [self.element._cos_rot_s, -self.element._sin_rot_s],
                [self.element._sin_rot_s,  self.element._cos_rot_s]
            ])
            
            rotated_corners = corners @ rotation_matrix.T
            ext_rect = np.max(rotated_corners[:,1])
            
            if ext_rect < 0:
                print("ERROR: rectangle extent from rectellipse is negatif")
            
            ext = np.min([ext_ellipse, ext_rect])
            if ext < 0:
                print("ERROR: extent from rectellipse is negatif")
            
            return -np.abs(ext) + self.element.shift_y, np.abs(ext) + self.element.shift_y

class RaceTrackAperture(ApertureElement):
    def __init__(self, element, name):
        super().__init__(element)
        self.name = name
    
    def compute_x_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            rect = RectangularAperture(self.element, self.name)
            return rect.compute_x_extent()
    
        else:
            rotation_matrix = np.array([
                    [self.element._cos_rot_s, -self.element._sin_rot_s],
                    [self.element._sin_rot_s,  self.element._cos_rot_s]
                ])
            
            ellipse_centers = np.array([[self.element.min_x+self.element.a, self.element.min_y+self.element.b],
                                        [self.element.max_x -self.element.a, self.element.min_y + self.element.b],
                                        [self.element.max_x - self.element.a, self.element.max_y - self.element.b],
                                        [self.element.min_x + self.element.a, self.element.max_y - self.element.b]])
            
            ellipse_centers_rot = ellipse_centers @ rotation_matrix.T
            ellipses = np.array([xt.LimitEllipse(a= self.element.a, b=self.element.b, shift_x = self.elementlipse_centers_rot[i,0], shift_y = self.elementlipse_centers_rot[i,1], _cos_rot_s = self.element._cos_rot_s, _sin_rot_s = self.element._sin_rot_s) for i in range(4)])
            
            x_exts = []
            for ellipse in ellipses:
                el = EllipticalAperture(ellipse, self.name + '_ellipse')
                x_min, x_max = el.compute_x_extent()
                x_exts.append(np.array([x_min, x_max]))
            
            x_exts = np.array(x_exts)
                
            return np.min(x_exts[:,0]) + self.element.shift_x, np.max(x_exts[:,1]) + self.element.shift_x
    
    def compute_y_extent(self):
        if (np.abs(self.element._cos_rot_s) > 1 and np.abs(self.element._sin_rot_s) > 1) or (np.abs(self.element._sin_rot_s) < 0.00001):
            rect = RectangularAperture(self.element, self.name)
            return rect.compute_x_extent()
    
        else:
            rotation_matrix = np.array([
                    [self.element._cos_rot_s, -self.element._sin_rot_s],
                    [self.element._sin_rot_s,  self.element._cos_rot_s]
                ])
            
            ellipse_centers = np.array([[self.element.min_x+self.element.a, self.element.min_y+self.element.b],
                                        [self.element.max_x -self.element.a, self.element.min_y + self.element.b],
                                        [self.element.max_x - self.element.a, self.element.max_y - self.element.b],
                                        [self.element.min_x + self.element.a, self.element.max_y - self.element.b]])
            
            ellipse_centers_rot = ellipse_centers @ rotation_matrix.T
            ellipses = np.array([xt.LimitEllipse(a= self.element.a, b=self.element.b, shift_x = self.elementlipse_centers_rot[i,0], shift_y = self.elementlipse_centers_rot[i,1], _cos_rot_s = self.element._cos_rot_s, _sin_rot_s = self.element._sin_rot_s) for i in range(4)])
            
            y_exts = []
            for ellipse in ellipses:
                el = EllipticalAperture(ellipse, self.name + '_ellipse')
                y_min, x_max = el.compute_y_extent()
                y_exts.append(np.array([y_min, y_max]))
            
            y_exts = np.array(y_exts)
                
            return np.min(y_exts[:,0]) + self.element.shift_y, np.max(y_exts[:,1]) + self.element.shift_y

class ApertureCalculator:
    def __init__(self, line):
        self.line = line
