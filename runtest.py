#!/usr/bin/env python

## python 2.7.8

# it uses JUnit5

import sys
import os
import os.path
import re
import shutil
import subprocess
import time
import tempfile
from distutils.dir_util import copy_tree
from distutils.errors import DistutilsFileError
import datetime

# some convenience global variables
global start_dir
global junit_path


# read a file containing one string per line returning the
# strings as a sorted list


def read_lines(fname):
	lines = []
	with open(fname, "r") as f:
		for line in f:
			line = line.strip()
			if line:
				lines.append(line)
	lines.sort()
	return lines


# parse the command line arguments passed to check.py
# returns three lists
# 1 the list of java files
# 2 the list of group files
# 3 the list of all other files
#
# the first 4 arguments are:
# 1 the name of this program
# 2 the course number - removed
# 3 the assignment name - removed
# 4 the user name of the submitter
def parse_args(args):
	user = args[1]
	srcs = []
	group = []
	other = []
	files = args[2:]
	for f in files:
		filename, ext = os.path.splitext(f)
		if ext == ".java":
			srcs.append(f)
		elif f == "group.txt":
			group = read_lines("group.txt")
		else:
			other.append(f)
	srcs.sort()
	other.sort()
	return user, srcs, group, other


# match a list of paths (exp) to a list of files (got)
# returns true if every file in got matches a file in
# exp when the leading directories are stripped from exp
# also returns the list of expected filenames with leading
# directories stripped
def match_exp(exp, got):
	# strip the directory name from the filename in exp
	expfilenames = []
	for p in exp:
		fname = os.path.basename(p)
		expfilenames.append(fname)
	expfilenames.sort()
	return (expfilenames == got), expfilenames


# copies submitted source files and test files into a
# temporary directory for compilation and testing
# returns the absolute path of the temporary directory
def setup(user, srcs, xsrcs):
	# create the temporary directory
	tempdir = tempfile.mkdtemp()

	# runs from the assignment submit directory
	try:
		# copy the contents of the test directory into the user"s directory
		# cmd = "cp -r " + start_dir + "/_test/* " + tempdir
		# subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True)
		copy_tree(start_dir + "/_test", tempdir)

		# copy the submitted files into their expected directories
		for src, dest in zip(srcs, xsrcs):
			srcPath = sub_folder + user + "/" + src
			destPath = tempdir + "/src/" + dest
			# print("copying " + srcPath + " --> " + destPath)
			shutil.copy(srcPath, destPath)

	except subprocess.CalledProcessError as e:
		shutil.rmtree(tempdir)
		system_error(e)

	except DistutilsFileError as e:
		print_system_error(str(e))

	return tempdir


# checks if each member of a group is a possibly valid username
# valid usernames begin with a lowercase letter and contain only
# lowercase letters and digits
# returns the empty string if the group is ok and an error string
# otherwise
def validate_group(group):
	regex = "^[a-z][a-z0-9]*$"
	prog = re.compile(regex)
	err_str = ""
	for member in group:
		if not prog.match(member):
			err_str += member + " is not a valid user name\n"
	return err_str


# compile a list of java programs located in a temporary directory
# assumes the working directory for javac is tempdir/src
# tempdir is the absolute path to the temporary directory
def compile_java(tempdir, xsrcs, is_suite=False):
	try:
		# compile
		working_dir = tempdir + "/src"

		if not os.path.isdir(working_dir):
			err_str = "compile_java: a directory that should exist does not exist\n"
			err_str += working_dir
			print_system_error(err_str)

		for srcfile in xsrcs:
			if not os.path.exists(working_dir + "/" + srcfile):
				err_str = "compile_java: a file that should exist does not exist\n"
				err_str += srcfile
				print_system_error(err_str)

			# cmd = "ls -la; pwd; exit 1";
			cmd = "javac -encoding ISO-8859-1 -cp .:"+ junit_path + " " + srcfile
			subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, cwd=working_dir)

		return ""
	except subprocess.CalledProcessError as e:
		if is_suite:
			# a test suite should not fail to compile
			system_error(e)

		output = e.output
		cmd = e.cmd
		err_str = "YOUR SUBMISSION FAILED TO COMPILE for " + srcfile  + "\n"
		err_str += "Here is the compiler output:\n\n{}".format(output)
		#print err_str
		return err_str

# run a list of junit test suites located in a temporary directory
# tempdir is the absolute path to the temporary directory
# old --- uses subprocess.check_output which is not timed-out
def run_test_suites_old(tempdir, suite):
	working_dir = tempdir + "/src"
	try:
		#for suite in suites:
			# strip the .java off the suite name if needed
			suite_name, ext = os.path.splitext(suite)

			# replace / with .
			suite_name = suite_name.replace('/', '.')

			junit_options = " --disable-banner --disable-ansi-colors --details=tree --details-theme=ascii --fail-if-no-tests"
			cmd = "java -jar " + junit_path + " --class-path=" + working_dir + " -c " + suite_name + junit_options;
			#print ("attempting => " + cmd)
			subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, cwd=working_dir)
	except subprocess.CalledProcessError as e:
			regex = "^\d+\).*"
			test_output_start = re.compile(regex)
			output = ""
			output_lines = e.output.split("\n")
			for line in output_lines:
				tmpline = line
				tmpline = tmpline.strip();
				if not tmpline.startswith("at"):
					if test_output_start.match(tmpline):
						output += "\n" + line + "\n"
					else:
						output += line + "\n"
			err_str = "\n\nYOUR SUBMISSION FAILED SOME UNIT TESTS for " + suite_name + "\n"
			err_str += "Here is the test output:\n\n{}".format(output)
			return err_str
	return ""

def run_test_suites(tempdir, tester):
	working_dir = tempdir + "/src"
	tester, ext = os.path.splitext(tester)

	# replace / with . to extract the tester full class name
	tester = tester.replace('/', '.')

	junit_options = " --disable-banner --disable-ansi-colors --details=tree --details-theme=ascii --fail-if-no-tests --include-engine junit-jupiter --exclude-engine junit-vintage"
	cmd = "java -jar " + junit_path + " -cp=" + working_dir + " -c " + tester + junit_options;

	timeout = 10
	cmd = "timeout -k 0.5 {} {}".format(timeout, cmd)
	p = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	(output, err) = p.communicate()
	
	if(not output):
		print("Could not run testers within {} seconds: tester-timed-out!".format(timeout))
		print("----------------------------------------------------------------------")
		print(err)
		err = "timed-out"
	else:
		print(output)
		print("----------------------------------------------------------------------")
		print(err)

	return err

def process_failed_output(output_lines):
	# remove every line that begins with "at"
	num_all_tests = re.compile("^\[\s+\d+\Wtests found\s+\]")
	num_sucs_tests = re.compile("^\[\s+\d+\Wtests successful\s+\]")
	num_fail_tests = re.compile("^\[\s+\d+\Wtests failed\s+\]")

	output = ""
	for line in output_lines:
		if num_all_tests.match(line) or num_sucs_tests.match(line) or num_fail_tests.match(line):
			output += line + "\n"

	cmd = e.cmd
	err_str = "\n\nYOUR SUBMISSION FAILED SOME UNIT TESTS\n"
	err_str += "Here is the test output:\n\n{}".format(output)
	#err_str += ">>>  YOUR WORK WAS SUBMITTED.  <<<\n"
	#err_str += ">>>  YOU MAY RE-SUBMIT AFTER FIXING YOUR ERRORS.  <<<\n"
	return err_str


# run the style checker on a list of source files located in
# a temporary directory
# tempdir is the absolute path to the temporary directory


def check_style(tempdir, xsrcs):
	working_dir = tempdir + "/src"
	try:
		for src in xsrcs:
			cmd = "java -jar /eecs/dept/course/2017-18/F/2030/jar/checkstyle-5.6-all.jar " + \
						"-c /eecs/dept/course/2017-18/F/2030/jar/EECS2030_checks.xml " + \
						src
			subprocess.check_output(cmd, stderr=subprocess.STDOUT, shell=True, cwd=working_dir)
	except subprocess.CalledProcessError as e:
		output = e.output
		err_str = "\nHere is the style checker output:\n\n{}".format(output)
		err_str += "In eclipse, use <Ctrl+Shift+F> to auto format your code, or\n"
		err_str += "select the code, right-click and choose Source -> Format\n\n"
		return err_str
	return ""


# convert a subprocess.CalledProcessError into an error message
# and exits the submit
# does not remove the submitted files
def system_error(e):
	output = e.output
	cmd = e.cmd
	ret = e.returncode
	if isinstance(output, basestring):
		output = output.strip()
	err_str = "{}\ncaused by: {}\nreturn code: {}".format(output, cmd, ret)
	print_system_error(err_str)



def print_system_error(err_str):
	msg = "There was a system error with your submission.\n" + \
			"Please email the following error message to asawas@eecs.yorku.ca:\n\n" + \
			err_str
	print msg
	sys.exit(1)


# deletes the submission and exits
def unsubmit(msg=""):
	msg += "\n>>>  REMOVING ALL SUBMITTED FILES.  <<<\n"
	print msg
	folder = sub_folder + the_user
	for the_file in os.listdir(folder):
		file_path = os.path.join(folder, the_file)
		try:
			if os.path.isfile(file_path):
				os.unlink(file_path)
			elif os.path.isdir(file_path):
				shutil.rmtree(file_path)
		except Exception as e:
			print(e)
	sys.exit()

# check if the submission is allowed
def is_submission_allowed(deadline, exception_users=[]):
	# are we still within the deadline
	now = datetime.datetime.now()
	if (now > (deadline + datetime.timedelta(hours=4))) :
		if (the_user in exception_users) and (now <= (deadline + datetime.timedelta(days=2))) :
			return True
		else:
			return False
	else:
		return True

if __name__ == "__main__":
	# initialize globals
	global start_dir
	start_dir = sys.path[0]

	# check command line args
	if (len(sys.argv)<3):
		print ("Expecting 3 or more arguments:")
		print ("Usage: " + sys.argv[0] + " <userdir> <submitted files>")
		exit()



	#global class_path
	#class_path = "-classpath " + ".:../_jar/*"
	global junit_path
	junit_path = "/eecs/dept/course/2018-19/S/2030/jar5/junit-platform-console-standalone-1.7.0.jar" #"/eecs/dept/grading/2020-21/F/2030/work/_jar/*"

	global the_user
	
	# submission folder
	global sub_folder
	sub_folder = start_dir + "/s/"


	# read tester.txt to get the list of unit tester paths
	testers = read_lines(start_dir + "/tester.txt")

	# read suite.txt to get the list of test suites
	suites = read_lines(start_dir + "/suite.txt")

	# read java.txt to get the list of expected java file paths
	xsrcs = read_lines(start_dir + "/java.txt")

	# read other.txt to get the list of expected other file paths
	if os.path.isfile(start_dir + "/other.txt"):
		xother = read_lines(start_dir + "/other.txt")
	else:
		xother = []

	# parse args to check if args contains the expected files
	user, srcs, group, other = parse_args(sys.argv)
	the_user = user
	print "============================="
	print "Processing user: " + the_user
	print "============================="

	# this will check the submission deadline and print a notice msg.
	# it shall not delete the submission because someone might resubmit the files
	#if (not is_submission_allowed(datetime.datetime(2019, 5, 26, 23, 59, 59), ["nzoibi98"])):
	#	print("\n\n>>> Notice: Deadline is passed for submission <<< \n\n")
		#sys.exit()

	match_srcs, xsrcs_nodirs = match_exp(xsrcs, srcs)
	match_other, xother_nodirs = match_exp(xother, other)
	if (not match_srcs) or (not match_other) :
		msg = "ERROR We expected the files:\n\n" + "\n".join(xsrcs_nodirs + xother_nodirs)
		msg += "\n\nbut you submitted the files:\n\n" + "\n".join(srcs + other)
		#msg += "\n\nPlease try submitting again with the expected files\n\n"
		#unsubmit(msg)

	# parse args to check if args contains group.txt
	#if group:
	#	err_str = validate_group(group)
	#	if err_str:
	#		print "There are errors in your group.txt file:\n"
	#		print err_str
	#		print "\ngroup.txt should consist of exactly one user name per line"
	#		print "and nothing else."
	#		print "\n>>>  YOUR WORK WAS NOT SUBMITTED <<<\n"
	#		sys.exit()
	#	print "This is a group submission with group members:\n\n" + "\n".join(group) + "\n"

	print "Compiling files .."
		
	# get ready for compiling
	tempdir = setup(user, srcs, xsrcs)

	# compile the files
	c_err = compile_java(tempdir, xsrcs)
	if(c_err != ""):
		print("------ Error compiling ----")
		print(c_err)
		shutil.rmtree(tempdir)
		exit()

	#print "\t.. compiled xsrcs"

	# compile the unit testers and suites
	c_err = compile_java(tempdir, testers)
	if(c_err != ""):
		print("------ Error compiling ----")
		print(c_err)
		shutil.rmtree(tempdir)
		exit()
	#print "\t.. compiled testers"

	if len(suites) != 0:
		compile_java(tempdir, suites)
		#print "\t.. compiled suites"

	# run the tests or test suites
	if len(suites) == 0:
		suites = testers
		
	print "Running tests.."
	# run the test suites
	err_str = ""
	for s in suites:
		print "=> test: " + s
		err_str += run_test_suites(tempdir, s)

	if not err_str:
		print "Unit tests successfully run on your submission."
	else:
		print "Unit tests could not run on your submission."
#		print err_str

	# run checkstyle
	if(0):
		style_err_str = check_style(tempdir, xsrcs)
		print ""
		# produce a report
		if not style_err_str:
			print "Your submission passed the basic style checks."
		else:
			print "Your submission failed some basic style checks."
			print style_err_str

	print "\nYour submission has been successfully processed."

	#shutil.rmtree(tempdir)