#!/usr/bin/env bash


# run the test for each submission. 
# The submissions are identified by the existance of the java file "Lab1.java"
# It calls the python script "runtest.py" that is based on Burton's script to run JUnit test for submitted files.

for d in s/*/Account.java ; do
	dir="$(echo $d | cut -d'/' -f 2)"
	echo "Running $dir"
	c="$(runtest.py "$dir" Account.java | tee s/"$dir"/out.txt)"
done
