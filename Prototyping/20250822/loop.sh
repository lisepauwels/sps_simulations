#!/bin/bash
for i in {8..329}
do
    echo "################# $i #################"
    python variable_starting_point.py "$i"
done
