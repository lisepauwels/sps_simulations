#!/bin/bash

LCGpath=/cvmfs/sft.cern.ch/lcg/views/LCG_107/x86_64-el9-gcc13-opt/setup.sh
bdsimpath=/eos/home-f/fvanderv/Software/bdsim/install/  # Can be left unchanged if BDSIM is not needed


# Source Python environment from cvmfs
source $LCGpath
retVal=$? # Check if the source command was successful
if [ $retVal -ne 0 ]
then
    echo "Failed to source LCG"
    exit $retVal  # Kill the job to avoid needless priority
fi

# Source other environments
for env in "$@"
do
    if [ "$env" = "geant4" ]
    then
        source ${bdsimpath}bin/bdsim.sh
        retVal=$?
        if [ $retVal -ne 0 ]
        then
            echo "Failed to source BDSIM"
            exit $retVal
        fi
    # elif # other environments can be added here
    else
        echo "Unknown argument: $env"
        exit 1
    fi
done
