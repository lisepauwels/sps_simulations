#!/bin/bash
base="/Users/lisepauwels/sps_simulations/Prototyping/20251017/results"

find "$base/optimalised_apertures" -type d -name "DPpos" | while read -r dir; do
    # Build the corresponding correct destination path
    newdir="${dir/optimalised_apertures/optimised_apertures}"

    # Create destination directory if needed
    mkdir -p "$newdir"

    echo "Moving contents from:"
    echo "  $dir"
    echo "to:"
    echo "  $newdir"
    echo

    # Move files safely
    mv "$dir"/* "$newdir"/
done
