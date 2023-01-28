#!/usr/bin/env bash


# this script reads the file out.txt and prints the result of each test case
# It relies on the python script process_output_one.py to process the output file 'out.txt'

echo "$(process_output.py Adam\ Hadad_1258443_assignsubmission_file_ -header)"
for d in s/*/ ; do
	dir="$(echo $d | cut -d'/' -f 2)"
	echo "$(process_output.py "$dir")"
done
