#!/usr/bin/env bash

# Usage: ./job.sh -p 834 -n TestRun -e geant4 -c python scripts/pencil_lossmap.py scriptargs


# Parse arguments
set -euo pipefail
processid=""
studyname=""
environments=()
pycmd=()
while [[ $# -gt 0 ]]
do
    case "$1" in
        -n|--studyname)
            studyname="${2:?Missing value for $1}"
            shift 2
            ;;
        -p|--processid)        # Optional process ID (only for logging purposes)
            processid="${2:?Missing value for $1}"
            shift 2
            ;;
        -e|--environment)  # Optional environment arguments to be passed to environment.sh (those cannot start with '-')
            shift
            while [[ $# -gt 0 && "$1" != -* ]]
            do
                environments+=("$1")
                shift
            done
            if [[ ${#environments[@]} -eq 0 ]]
            then
                echo "Error: -e/--environment requires at least one value" >&2
                exit 1
            fi
            ;;
        -c|--command)
            shift
            pycmd=("$@")   # grab the rest verbatim
            break
            ;;
        --)
            shift
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            echo "Unexpected positional argument: $1 (use -c/--command for the python command)" >&2
            exit 1
            ;;
    esac
done
if [[ -z "$studyname" ]]
then
  echo "Error: -n/--studyname is required" >&2
  exit 1
fi
if [[ ${#pycmd[@]} -eq 0 ]]
then
  echo "Error: -c/--command is required and must be followed by the full python command" >&2
  exit 1
fi
if [[ "${pycmd[0]}" != "python" && "${pycmd[0]}" != "python3" ]]
then
  echo "Error: -c/--command must start with 'python' (or 'python3'), got: ${pycmd[0]}" >&2
  exit 1
fi

set --

echo "uname -r:" `uname -r`


# Unpack all files that were spooled to the node
tar -xzf files_${studyname}.tar.gz


# Source the environment
sleep 60 # Wait for the cvmfs to be mounted
set +u
source environment.sh "${environments[@]}"
set -u


# Check the python version
echo "Python path: "$(which "${pycmd[0]}")
echo "Python executable: $("${pycmd[0]}" -c 'import sys; print(sys.executable)' 2>&1)"
echo "Python version:    $("${pycmd[0]}" --version 2>&1)"
echo "ls:"
ls


# Source the xsuite environment
mkdir xsuite_env
tar -xzf xsuite_env*.tar.gz -C xsuite_env
echo "ls after unpacking:"
ls
set +u
source xsuite_env/bin/activate
set -u


# Run the job
echo $( date )"    Running "${studyname}" Process ID "${processid}"."
echo $( date )"    Using command: "${pycmd[@]}
echo
"${pycmd[@]}"
echo
echo $( date )"    Done"
set +u
deactivate
set -u
for f in files_${studyname}.tar.gz xsuite_env*.tar.gz xsuite_env data scripts environment.sh job.sh
do
    rm -r $f || true  # Do not fail if the file is not there
done
