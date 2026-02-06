import sys
import json
import numpy as np
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless, no Tk, to avoid issues with parallellisation

import xobjects as xo
import xtrack as xt
import xcoll as xc


def combine_lossmaps(study_path, output_name=None, *, result_path=None, plot_path=None, verbose=True):
    # Combine loss map files and plot
    study_path = Path(study_path).resolve()
    if result_path is None:
        result_path = study_path.parents[2] / 'results'
    result_path = Path(result_path).resolve()
    if plot_path is None:
        plot_path = study_path.parents[2] / 'plots'
    plot_path = Path(plot_path).resolve()
    if output_name is None:
        output_name = ''
    else:
        output_name = output_name + '_'

    files = np.array(list(study_path.glob(f'job_*/lossmap_*.json')))
    if len(files) == 0:
        if verbose:
            print('No lossmap files found!')
        return
    if verbose:
        print(f'Found {len(files)} lossmap files')
    lossmap_types = np.unique([f.stem for f in files])
    if verbose:
        print(f"Lossmap types: {', '.join(lossmap_types)}")

    for lm_type in lossmap_types:
        if verbose:
            print(f'  -> Processing lossmap type: {lm_type}')
        lm = xc.LossMap.from_json(study_path.glob(f'job_*/{lm_type}.json'))
        lm.save_summary(result_path / f'{output_name}{lm_type}.out')
        lm.to_json(result_path / f'{output_name}{lm_type}.json')
        lm.plot(show=False, savefig=plot_path / f'{output_name}{lm_type}.pdf')


def combine_particle_dict(study_path, output_name=None, *, result_path=None, verbose=True):
    # Combine particle dict files
    study_path = Path(study_path).resolve()
    if result_path is None:
        result_path = study_path.parents[2] / 'results'
    result_path = Path(result_path).resolve()
    if output_name is None:
        output_name = ''
    else:
        output_name = output_name + '_'

    files = np.array(list(study_path.glob(f'job_*/particles_dict_*.json')))
    if len(files) == 0:
        if verbose:
            print('No particles_dict files found!')
        return
    if verbose:
        print(f'Found {len(files)} particles_dict files')
    particles_dict_types = np.unique([f.stem for f in files])
    if verbose:
        print(f"Particles_dict types: {', '.join(particles_dict_types)}")

    for pd_type in particles_dict_types:
        if verbose:
            print(f'  -> Processing particles_dict type: {pd_type}')
        final_data = None
        for file in study_path.glob(f'job_*/{pd_type}.json'):
            with file.open('r') as fp:
                data = json.load(fp)
            if 'state' not in data:
                raise ValueError("Invalid particles_dict file (missing 'state')!")
            data = {kk: np.array(vv) for kk, vv in data.items()}
            mask = data['state'] > xt.particles.LAST_INVALID_STATE
            data = {kk: vv[mask] for kk, vv in data.items()}
            if final_data is None:
                final_data = data
            else:
                for kk, vv in data.items():
                    final_data[kk] = np.concatenate([final_data[kk], vv])
        with (result_path / f'{output_name}{pd_type}.json').open('w') as fp:
            json.dump(final_data, fp, cls=xo.JEncoder)


if __name__=="__main__":
    study = sys.argv[1]
    case = sys.argv[2]
    study_path = Path.cwd().parent / 'studies' / study / case
    print(f'Processing {study_path}')
    output_name = f'{study}_{case}'
    combine_lossmaps(study_path, output_name, result_path=None, plot_path=None, verbose=True)
    combine_particle_dict(study_path, output_name, result_path=None, verbose=True)
