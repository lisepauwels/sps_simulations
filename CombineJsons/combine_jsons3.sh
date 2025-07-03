#!/bin/bash

BASE_DIR="/eos/user/l/lpauwels/sps_simulations/archive/MomentumAcceptance/tidp_bump_scan/job_results"
RESULTS_DIR="/eos/user/l/lpauwels/sps_simulations/archive/MomentumAcceptance/tidp_bump_scan/studies_results"


for bump_dir in "$BASE_DIR"/*; do
    bump_mm=$(basename "$bump_dir")
    # Only keep bump_mm values between -50.0 and -36.0
    if ! awk "BEGIN {exit !($bump_mm >= -50.0 && $bump_mm <= -36.0)}"; then
        continue
    fi
    echo ${bump_mm}
    
    part_files=()

    for job_dir in "$bump_dir"/job*; do
        shopt -s nullglob
        matches=( "$job_dir"/part.json )
        shopt -u nullglob

        if (( ${#matches[@]} )); then
            for f in "${matches[@]}"; do
                part_files+=("$f")
            done
        else
            echo "  Missing part.json in $job_dir"
        fi
    done

    if [ "${#part_files[@]}" -gt 0 ]; then
        bump_tag="b$( [[ "$bump_mm" == -* ]] && echo "m" || echo "p" )${bump_mm#-}mm"
        output_file="${RESULTS_DIR}/${bump_tag}.json"

        echo "Merging ${#part_files[@]} files into $output_file"
        python3 combine_jsons_script.py particles "${part_files[@]}" "$output_file"

    else
        echo "No JSON files found for bump value ${bump_mm} mm"
    fi
done
