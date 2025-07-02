#!/bin/bash
jobid=$1
bump=$2

set --

# Source python environment from cvmfs
sleep 60 # Wait for the cvmfs to be mounted
echo "uname -r:" `uname -r`
source /cvmfs/sft.cern.ch/lcg/views/LCG_106/x86_64-el9-gcc13-opt/setup.sh
# Check if the source command was successful, otherwise, kill the job to avoid needless priority
retVal=$?
if [ $retVal -ne 0 ]
then
    echo "Failed to source LCG_106"
    exit $retVal
fi

# Check the python version
echo "Python path: "$(which python)
echo "Python version: "$(python --version)
echo "ls:"
ls

# Unpack all files that were spooled to the node
tar -xzf files.tar.gz
echo "ls after unpacking:"
ls

# python3 run_off_momentum_LM.py $line
python3 rf_sweep_with_bump_script.py $bump