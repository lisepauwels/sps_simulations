import cernlayoutdb as layout
import xtrack as xt
import numpy as np

class ManageApertures:
    def __init__(self, line, machine, version):
        self.line = line
        self.machine = machine
        self.version = version

    def get_ldb_info(self):
        db = layout.DB()
        aperture_info_list = db.get_apertures(machine=self.machine, version=self.version)
        names_db_line = np.array([aperture_info_list[i][1].lower() for i in range(len(aperture_info_list))])
        aperture_elements = {}

        for i, name in enumerate(names_db_line):
            aper_type = str(aperture_info_list[i][4][0])
            max_x = aperture_info_list[i][4][1][0]
            max_y = aperture_info_list[i][4][1][1]
            a = aperture_info_list[i][4][1][2]
            b = aperture_info_list[i][4][1][3]

            if aper_type == 'CIRCLE' or aper_type == 'ELLIPSE':
                aperture_elements[name.lower()] = xt.LimitEllipse(a=a, b=b)
            elif aper_type == 'RECTANGLE':
                aperture_elements[name.lower()] = xt.LimitRect(min_x=-max_x, max_x=max_x, min_y=-max_y, max_y=max_y)
            elif aper_type == 'RECTELLIPSE':
                aperture_elements[name.lower()] = xt.LimitRectEllipse(max_x=max_x, max_y=max_y, a=a, b=b)
            elif aper_type == 'RACETRACK':
                aperture_elements[name.lower()] = xt.LimitRacetrack(min_x=-max_x, max_x=max_x, min_y=-max_y, max_y=max_y, a=a, b=b)
            else:
                ValueError(f'{name.lower()} has aperture type {aper_type}, which is not known !')
        
        return aperture_elements
        

    
    def associated_apertures_naming(self, complementary_apertures=None, isThick=True):
        apertures_db = self.get_ldb_info()

        for name in self.line.element_names:
            if self.line[name].__class__.__name__ not in ['Drift', 'Marker'] and not self.line[name].__class__.__name__.startswith('Drift'):
                if self.line[name].__class__.__name__ == 'Drift':
                    print(name)
                    
                if name in apertures_db:
                    setattr(self.line[name], 'apertures', {f'{name}_aper_upstream' : apertures_db[name].copy(), 
                                                            f'{name}_aper_downstream' : apertures_db[name].copy()})
                else:
                    if complementary_apertures is not None:
                        matching_aper_key = next((key for key in complementary_apertures if name.startswith(key)), None)
                        if matching_aper_key:
                            setattr(self.line[name], 'apertures', {f'{name}_aper_upstream' : complementary_apertures[matching_aper_key]['xt_elem'], 
                                                            f'{name}_aper_downstream' : complementary_apertures[matching_aper_key]['xt_elem']})
                        else:
                            print(f'No matching aperture for {name} in complementary dictionary')
                    else:
                        print(f'{name} has no given aperture, passing assignment')
    
    def install_apertures(self):
        insert_names = [
            {f'{name}_aper_upstream': index, f'{name}_aper_downstream': index + 1}
            for index, name in enumerate(self.line.element_names)
            if hasattr(self.line[name], 'apertures')
        ]

        insert_names = {kk: vv for dct in insert_names for kk, vv in dct.items()}
        idxs = list(insert_names.values())
        names = list(insert_names.keys())
        max_length = max(max(map(len, self.line.element_names)), max(map(len, names)))
        element_names = np.array(self.line.element_names, dtype=f'<U{max_length}')
        names = np.array(names, dtype=f'<U{max_length}')
        element_names = np.insert(element_names, idxs, names)

        # Update insert_elements to handle variable-length keys
        insert_elements = [
            {
                f'{name}_aper_upstream': self.line[name].apertures[f'{name}_aper_upstream'].copy(),
                f'{name}_aper_downstream': self.line[name].apertures[f'{name}_aper_downstream'].copy()
            }
            for name in self.line.element_names
            if hasattr(self.line[name], 'apertures')
        ]
        insert_elements = {kk: vv for dct in insert_elements for kk, vv in dct.items()}

        # Update line's element names and element dictionary
        self.line.element_names = element_names.tolist()
        self.line.element_dict = {**self.line.element_dict, **insert_elements}

    def find_associated_apertures(self):
        associated_apertures = {}
        for name in self.line.element_names:
            if self.line[name].__class__.__name__ not in ['Drift', 'Marker'] and not self.line[name].__class__.__name__.startswith('Drift') and not self.line[name].__class__.__name__.startswith('Limit'):
                idx = self.line.element_names.index(name)
                associated_apertures[name] = {}
                #check that aper is in previous and next element and name of the element as well
                aper_upstream = self.line.element_names[idx-1]
                aper_downstream = self.line.element_names[idx+1]

                for aper in [aper_upstream, aper_downstream]:

                    idx_aper = self.line.element_names.index(aper)
                    if idx_aper < idx: case='upstream'
                    else: case='downstream'

                    if aper.__class__.__name__.startswith('Limit'):
                        print(f'{name} has no {case} aperture')
                    else:
                        associated_apertures[name][f'aper_{case}'] = aper
                        if 'aper' not in aper or name not in aper:
                            print(f'{case} aper of {name} found but weird formatting: {aper}')
                
        return associated_apertures
                
