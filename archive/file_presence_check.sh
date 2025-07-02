#!/bin/bash

# Directory containing job_* subdirectories
JOB_DIR=/eos/user/l/lpauwels/ht_condor_sps_tracking_results/blowup/run_29.01.2025/with_coll/

# Check for missing JSON files
echo "Checking for missing JSON files..."
find "$JOB_DIR" -type d -name "job_*" | while read dir; do
    if [[ ! -f "$dir/blowup_LM_V_adt_0.12.json" ]]; then
        echo "Missing: $dir"
    fi
done

# Check for corrupt JSON files
echo "Checking for corrupt JSON files..."
find ${JOB_DIR}job_* -type f -name "blowup_LM_V_adt_0.12.json" | while read -r file; do
    if [[ ! -s "$file" ]]; then
        echo "Empty file: $file"
    elif ! jq empty "$file" >/dev/null 2>&1; then
        echo "Corrupt JSON: $file"
    fi
done
