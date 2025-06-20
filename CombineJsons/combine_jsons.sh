#!/bin/bash

JOB_DIR=/eos/user/l/lpauwels/Simulations/BeamSagittaStudies/job_results/scatter_bottleneck_coll
#echo $JOB_DIR

if [ -d $JOB_DIR ]; then
    echo "Directory exists."
else
    echo "Directory does not exist."
fi

# Gather all json files into lists
particles_files=()
LM_files=()

for dir in "$JOB_DIR"/job*/; do
    particle_file="${dir}particles_off_momentum_sweep_with_coll.json"
    LM_file="${dir}LM_off_momentum_sweep_with_coll.json"

    if [ -f "$particle_file" ] && [ ! -d "$particle_file" ]; then
        particles_files+=("$particle_file")
    fi

    if [ -f "$LM_file" ] && [ ! -d "$LM_file" ]; then
        LM_files+=("$LM_file")
    fi
done




# echo "Particles files:"
# printf '  %s\n' "${particles_files[@]}"


RESULTS_DIR=/eos/user/l/lpauwels/Simulations/BeamSagittaStudies

python3 combine_jsons_script.py LM "${LM_files[@]}" "$RESULTS_DIR/LM_basic_off_momentum_with_coll.json"
echo "LM files combination complete !"

python3 combine_jsons_script.py particles "${particles_files[@]}" "$RESULTS_DIR/particles_basic_off_momentum_with_coll.json"
echo "Particles files combination complete !"
