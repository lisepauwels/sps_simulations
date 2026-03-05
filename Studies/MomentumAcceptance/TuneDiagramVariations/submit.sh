#!/bin/bash

STUDYNAME=TuneDiagramVariations
JOBSFILE=example.jobs.yaml

ENVNAME=xcoll_0.9.2
environments=()

XSUITEPATH=/eos/home-l/lpauwels/Xsuite/
AFSSUBMISSIONPATH=/afs/cern.ch/work/l/lpauwels/SimulationSubmissions/

STUDYPATH=$(pwd -P)
# ENVPATH=${STUDYPATH}/envs/
ENVPATH=/eos/user/l/lpauwels/SimulationEnvs/
mkdir -p ${ENVPATH}
SPOOLPATH=${STUDYPATH}/spool/
mkdir -p $SPOOLPATH

# Get or create the xsuite environment
envfile=xsuite_env_${ENVNAME}.tar.gz
if [ ! -f ${ENVPATH}$envfile ]
then
    cd $SPOOLPATH
    echo "Sourcing environment..."
    source ${STUDYPATH}/submission_scripts/environment.sh "${environments[@]}"
    echo "Creating Xsuite environment..."
    python -m venv --system-site-packages build_venv
    source build_venv/bin/activate
    echo "Installing packages..."
    pip install -U pip setuptools wheel distutils setuptools-scm[toml]
    pip install ${XSUITEPATH}xobjects
    pip install ${XSUITEPATH}xdeps
    pip install ${XSUITEPATH}xtrack
    pip install ${XSUITEPATH}xpart
    pip install ${XSUITEPATH}xfields
    pip install ${XSUITEPATH}xcoll
    pip install --no-dependencies ${XSUITEPATH}xsuite
    echo "Prebuilding xsuite kernels..."
    xsuite-prebuild r
    # How to automatise for different environments?
    if [[ ${environments[*]} =~ (^|[[:space:]])"fluka"($|[[:space:]]) ]]
    then
        echo "Initializing FLUKA..."
        python ${STUDYPATH}/submission_scripts/fluka_init_eos.py
    fi
    if [[ ${environments[*]} =~ (^|[[:space:]])"geant4"($|[[:space:]]) ]]
    then
        echo "Initializing Geant4..."
        python ${STUDYPATH}/submission_scripts/geant4_init.py
    fi
    echo "Packing environment..."
    pip install venv-pack
    venv-pack -p build_venv -o ${ENVPATH}$envfile
    deactivate
    rm -r build_venv
    echo "Environment created."
    echo
    cd $STUDYPATH
fi


# Spool the necessary files
echo "Spooling files..."
if [ -f ${SPOOLPATH}files_${STUDYNAME}.tar.gz ]
then
    rm ${SPOOLPATH}files_${STUDYNAME}.tar.gz
fi
tar -C . -czf ${SPOOLPATH}files_${STUDYNAME}.tar.gz scripts data -C ${ENVPATH} $envfile -C ${STUDYPATH}/submission_scripts environment.sh
echo


# Prepare submission directory and submit the job
DIR=${AFSSUBMISSIONPATH}${STUDYNAME}/
mkdir -p $DIR
if [ -L $STUDYNAME ] || [ -f $STUDYNAME ]
then
    rm $STUDYNAME
fi
ln -fns $DIR $STUDYNAME

cp submission_scripts/job.sh $DIR
cp submission_scripts/submission.sub $DIR
echo "Generating job list..."
python submission_scripts/generate_jobs.py --spec $JOBSFILE --out ${DIR}jobs.list --preview
echo "Job list generated."
echo

cd $DIR
if [ ${#environments[@]} -gt 0 ]
then
    ENV_LIST="${environments[*]}"
    condor_submit NAME="$STUDYNAME" PATH="$STUDYPATH" ENV_LIST="$ENV_LIST" submission.sub
else
    condor_submit NAME="$STUDYNAME" PATH="$STUDYPATH" submission.sub
fi
