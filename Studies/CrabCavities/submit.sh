#!/bin/bash
globalstudy=CrabCavities
# studyname=InitialBottleneckShift2


mkdir -p spool
cd spool
if [ -f files.tar.gz ]
then
    rm files.tar.gz
    rm *.json
    rm *.py
fi
for f in xobjects xcoll xpart xtrack xdeps xfields
do
    cp -r /afs/cern.ch/work/l/lpauwels/Xsuite/$f/$f .
done

SUBMISSION_DIR=/eos/user/l/lpauwels/Simulations/${globalstudy}/submission_files
echo $SUBMISSION_DIR

line=cc_line.json
# python_script=run_off_momentum_LM.py
python_script=script.py

cp $SUBMISSION_DIR/$line .
cp $SUBMISSION_DIR/$python_script .

tar -czf files.tar.gz $line $python_script xobjects xcoll xpart xtrack xdeps xfields
rm -r xobjects xcoll xpart xtrack xdeps xfields
cd ..

DIR0=/afs/cern.ch/work/l/lpauwels/SimulationSubmissions/${globalstudy}/
DIR=/afs/cern.ch/work/l/lpauwels/SimulationSubmissions/${globalstudy}/

if [ -L htc_logs ]
then
    rm htc_logs
fi

if [ -L $DIR0 ]
then
    rm -r $DIR0
fi

mkdir $DIR0
mkdir -p $DIR
ln -fns $DIR htc_logs

pwd
ls -l
ls -L $DIR0
ls -L htc_logs

cp $SUBMISSION_DIR/job.sh $DIR
cp $SUBMISSION_DIR/submission.sub $DIR

cd htc_logs
echo htc_logs
ls
# cd ${studyname}
condor_submit submission.sub
