import json
import numpy as np
import sys
from pathlib import Path

def combine_particle_jsons(particle_files):
    combined_particle_data = {}

    for i, file in enumerate(particle_files):
        with open(file, 'r') as f:
            part_current = json.load(f)
        
        if i == 0:
            combined_particle_data = part_current
            nb_particles = max(part_current['particle_id'])+1
        else:
            for key in part_current.keys():
                if type(part_current[key]) == list:
                    if key == 'particle_id' or key == 'parent_particle_id':
                        combined_particle_data[key]+=list(map(int, np.array(part_current['particle_id']) + i*nb_particles))
                    
                    else:
                        combined_particle_data[key]+=part_current[key]

                else:
                    if type(combined_particle_data[key]) != list:
                        combined_particle_data[key] = [combined_particle_data[key], part_current[key]]
                    else:
                        combined_particle_data[key].append(part_current[key])
    return combined_particle_data

def combine_LM_jsons(LM_files):
    combined_LM_data = {
            'collimator': {'s': [], 'name': [], 'length': [], 'n': []},
            'aperture': {'s': [], 'name': [], 'n': []},
            'machine_length': 6911.5038,
            'interpolation': 0.1,
            'reversed': False
        }

    collimator_dict = {}  # To sum losses correctly
    aperture_dict = {}

    for file in LM_files: 
        with open(file, 'r') as f:
            LM_current = json.load(f)
        
        # --- Merge collimator data ---
        for i in range(len(LM_current['collimator']['s'])):
            key = (LM_current['collimator']['s'][i], LM_current['collimator']['name'][i])
            if key in collimator_dict:
                collimator_dict[key]["n"] += LM_current['collimator']['n'][i]
            else:
                collimator_dict[key] = {
                    "s": LM_current['collimator']['s'][i],
                    "name": LM_current['collimator']['name'][i],
                    "length": LM_current['collimator']['length'][i],
                    "n": LM_current['collimator']['n'][i]
                }

        # --- Merge aperture LM_current ---
        for i in range(len(LM_current['aperture']['s'])):
            key = (LM_current['aperture']['s'][i], LM_current['aperture']['name'][i])
            if key in aperture_dict:
                aperture_dict[key]["n"] += LM_current['aperture']['n'][i]
            else:
                aperture_dict[key] = {
                    "s": LM_current['aperture']['s'][i],
                    "name": LM_current['aperture']['name'][i],
                    "n": LM_current['aperture']['n'][i]
                }

    # Convert collimator dictionary back to lists
    sorted_collimator = sorted(collimator_dict.values(), key=lambda x: x["s"])
    combined_LM_data['collimator']['s'] = [entry["s"] for entry in sorted_collimator]
    combined_LM_data['collimator']['name'] = [entry["name"] for entry in sorted_collimator]
    combined_LM_data['collimator']['length'] = [entry["length"] for entry in sorted_collimator]
    combined_LM_data['collimator']['n'] = [entry["n"] for entry in sorted_collimator]

    # Convert aperture dictionary back to lists
    sorted_aperture = sorted(aperture_dict.values(), key=lambda x: x["s"])
    combined_LM_data['aperture']['s'] = [entry["s"] for entry in sorted_aperture]
    combined_LM_data['aperture']['name'] = [entry["name"] for entry in sorted_aperture]
    combined_LM_data['aperture']['n'] = [entry["n"] for entry in sorted_aperture]

    return combined_LM_data

type_combination = str(sys.argv[1])
files_list = sys.argv[2:-1]
output_file = Path(sys.argv[-1])
# print("sys.argv:", sys.argv)
# import pdb; pdb.set_trace() 

if type_combination=='LM':
    combined_data = combine_LM_jsons(files_list)

elif type_combination=='particles':
    combined_data = combine_particle_jsons(files_list)

else:
    AssertionError('Combination type is not known nor developped !')

with open(output_file, 'w') as f:
    json.dump(combined_data, f, indent=4)


if output_file.exists():
    print("Path exists")