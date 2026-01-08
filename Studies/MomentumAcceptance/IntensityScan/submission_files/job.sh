#!/bin/bash
jobid=$1
plane=$2
nn_error=$3
chroma=$4

set --

echo "Start: $(date)"

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
mkdir xsuite_env
tar -xzf xsuite_env*.tar.gz -C xsuite_env
echo "ls after unpacking:"
ls
source xsuite_env/bin/activate


if [[ "$nn_error" == "linear" && "$chroma" == "0.5" ]]; then
    line=sps_chroma_0.5.json

elif [[ "$nn_error" == "linear" && "$chroma" == "0.7" ]]; then
    line=sps_chroma_0.7.json

elif [[ "$nn_error" == "linear" && "$chroma" == "1.0" ]]; then
    line=sps_chroma_1.0.json

elif [[ "$nn_error" == "errors" && "$chroma" == "0.5" ]]; then
    line=sps_errors_chroma_0.5.json

elif [[ "$nn_error" == "errors" && "$chroma" == "0.7" ]]; then
    line=sps_errors_chroma_0.7.json

elif [[ "$nn_error" == "errors" && "$chroma" == "1.0" ]]; then
    line=sps_errors_chroma_1.0.json

fi

# line=off_mom_scan_line.json
echo $line
echo $plane
ls lines_rf_sweep_sim
python3 script.py lines_rf_sweep_sim/$line $plane

echo "End: $(date)"

rm -r xsuite_env lines_rf_sweep_sim script.py files.tar.gz xsuite_env*.tar.gz
