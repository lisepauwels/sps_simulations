#!/bin/bash

BASE_DIR="/eos/user/l/lpauwels/sps_simulations/MomentumAcceptance/tidp_scan/job_results"
RESULTS_DIR="/eos/user/l/lpauwels/sps_simulations/MomentumAcceptance/tidp_scan/studies_results"


for plane in "$BASE_DIR"/*; do
    mkdir -p $RESULTS_DIR/$plane
    for chroma in "$plane"/*; do
        echo ${chroma}
        chroma_val=$(basename "$chroma")
        echo ${chroma_val}
        part_files=()

        for job_dir in "$chroma"/job*; do
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
            output_file="${plane}/${chroma_val}.json"

            echo "Merging ${#part_files[@]} files into $output_file"
            python3 combine_jsons_script.py particles "${part_files[@]}" "$output_file"

        else
            echo "No JSON files found for chroma ${chroma} in plane ${plane}"
        fi
    done
done
