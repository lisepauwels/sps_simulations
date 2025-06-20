#!/bin/bash

BASE_DIR="/eos/user/l/lpauwels/Simulations/MDSimulations/job_results/LM_betatron_with_bump"
RESULTS_DIR="/eos/user/l/lpauwels/Simulations/MDSimulations/studies_results/LM_betatron_with_bump"
COPY_DIR="/eos/user/l/lpauwels/sps_simulations/SimulationsResults/MDResults/LM_betatron_with_bump"

mkdir -p "$COPY_DIR"

for bump_dir in "$BASE_DIR"/bump_*; do
    bump_name=$(basename "$bump_dir")
    bump_mm=$(basename "$bump_dir" | sed 's/^bump_//')

    LM_files=()

    for job_dir in "$bump_dir"/job*; do
        shopt -s nullglob
        matches=( "$job_dir"/LM_betatron_bump_*.json )
        shopt -u nullglob

        if (( ${#matches[@]} )); then
            for f in "${matches[@]}"; do
                LM_files+=("$f")
            done
        else
            echo "  Missing LM_betatron_bump_*.json in $job_dir"
        fi
    done

    if [ "${#LM_files[@]}" -gt 0 ]; then
        output_file="${RESULTS_DIR}/LM_betatron_with_bump_${bump_mm}mm.json"
        bump_tag="b$( [[ "$bump_mm" == -* ]] && echo "m" || echo "p" )${bump_mm#-}mm"

        echo "Merging ${#LM_files[@]} files into $output_file"
        python3 combine_jsons_script.py LM "${LM_files[@]}" "$output_file"

        echo "Copying to $COPY_DIR/${bump_tag}.json"
        cp "$output_file" "$COPY_DIR/${bump_tag}.json"
    else
        echo "No JSON files found for bump value ${bump_mm} mm (${bump_value} m)"
    fi
done