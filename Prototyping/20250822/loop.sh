#!/bin/bash
for i in {0..329}
do
    echo "################# $i #################"
    python variable_starting_point.py "$i"
done
