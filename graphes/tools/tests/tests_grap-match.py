#!/usr/bin/env python
import sys
import os
import subprocess
import tempfile

Red = "\x1b[1;31m";
Green = "\x1b[1;32m";
Blue = "\x1b[1;33m";
Color_Off = "\x1b[0m";


def main():
    test_dir = find_test_dir(sys.argv)
    if test_dir is None:
        print "Test graphs not found in directory"
        return 1

    n_tests, expected, pattern_paths, test_paths = parse_tests(test_dir)
    if n_tests == 0:
        print "No test found in directory " + test_dir
        return 1

    verbose = False
    for v in sys.argv:
        if v == "-v" or v == "--verbose":
            verbose = True

    error_total = 0
    print Blue + "Testing grap-match", Color_Off
    error_gm = test_grap_match_binary(verbose, None, "grap-match", n_tests, expected, pattern_paths, test_paths)
    error_gmpy = test_grap_match_binary(verbose, "python2", "grap-match.py", n_tests, expected, pattern_paths, test_paths)

    print_error_msg(error_total, "Total: " + str(error_total) + " errors found.")
    error_total = error_gm + error_gmpy


def print_error_msg(error_count, message):
    if error_count == 0:
        color = Green
    else:
        color = Red
    print color + message + Color_Off


def test_grap_match_binary(verbose, interpreter, program, n_tests, expected, pattern_paths, test_paths):
    error_count = 0
    if not os.path.isfile(program):
        print program + " not found."
        return 1

    for i in range(n_tests):
        if i >= 1 and verbose:
            print ""

        args = []
        tmp_pattern = None

        if len(pattern_paths[i]) == 1:
            args += pattern_paths[i]
        else:
            tmp_pattern = tempfile.NamedTemporaryFile()
            for path in pattern_paths[i]:
                data = open(path, "r").read()
                tmp_pattern.file.write(data)
            tmp_pattern.file.flush()
            args.append(tmp_pattern.name)
        args.append(test_paths[i])

        multiple_patterns_in_dot = False
        if len(pattern_paths[i]) == 1:
            lines = open(pattern_paths[i][0], "r").read().split("\n")

            found_beginning = False
            for l in lines:
                if len(l) >= 9 and (l[0] == "D" or l[0] == "d") and l[1:7] == "igraph":
                    if l.rstrip()[-1] == "{":
                        if found_beginning:
                            multiple_patterns_in_dot = True
                            break
                        found_beginning = True

        launcher = []
        if interpreter is not None:
            launcher.append(interpreter)
        launcher.append(program)

        command_label_tree = launcher + [] + args
        command_label_singletraversal = launcher + ["--single-traversal"] + args
        command_nolabel_tree = launcher + ["--no-check-labels"] + args
        command_nolabel_singletraversal = launcher + ["--no-check-labels", "--single-traversal"] + args

        if verbose:
            print Blue + "Running test", i, Color_Off
            print "Checking labels:"
        error_count += run_and_parse_command(verbose, i, command_label_tree, expected[i][0], "tree")
        if len(pattern_paths[i]) == 1 and not multiple_patterns_in_dot:
            error_count += run_and_parse_command(verbose, i, command_label_singletraversal, expected[i][0], "single traversal")

        if verbose:
            print "Not checking labels:"
        error_count += run_and_parse_command(verbose, i, command_nolabel_tree, expected[i][1], "tree")
        if len(pattern_paths[i]) == 1 and not multiple_patterns_in_dot:
            error_count += run_and_parse_command(verbose, i, command_nolabel_singletraversal, expected[i][1], "single traversal")

        if tmp_pattern is not None:
            tmp_pattern.file.close()

    return error_count


def run_and_parse_command(verbose, i, command, expected_traversals, algo):
    if verbose:
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
    else:
        FNULL = open(os.devnull, 'w')
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=FNULL)

    out, err = process.communicate()
    exitcode = process.returncode

    if exitcode != 0:
        print Red + " ".join(command) + " failed:" + Color_Off
        if err is not None:
            print err
        print out
        return 1

    lines = out.split("\n")
    found_traversals = None
    for l in lines:
        splitted = l.split(" ")
        if len(splitted) >= 3 and splitted[1] == "traversal(s)" and splitted[2] == "possible":
            found_traversals = int(splitted[0])

    if found_traversals is None:
        if not verbose:
            print " ".join(command) + ":"
        print Red + "Error: could not parse grap-match output." + Color_Off
        return 1
    else:
        if expected_traversals != found_traversals:
            if not verbose:
                print " ".join(command) + ":"
            print Red + str(found_traversals), "traversals possible in test graph (expected:", str(expected_traversals) + ") with " + algo + ".", Color_Off
            return 1
        else:
            if verbose:
                print Green + str(found_traversals), "traversals possible in test graph (expected:", str(expected_traversals) + ") with "+ algo + ".", Color_Off
    return 0


def parse_tests(test_dir):
    expected = dict()
    pattern_paths = dict()
    test_paths = dict()

    n_tests = 0
    while True:
        path = test_dir + "/" + "test" + str(n_tests)
        if os.path.isdir(path):
            expected_path = path + "/" + "expected_gtsi"
            test_path = path + "/" + "test.dot"

            expected_list = []
            if os.path.isfile(expected_path):
                data = open(expected_path, "r").read()
                splitted = data.split("\n")

                if len(splitted) < 2:
                    break
                else:
                    expected_list.append(int(splitted[0]))
                    expected_list.append(int(splitted[1]))

            n_pattern = 0
            pattern_list = []
            while True:
                pattern_path = path + "/" + "pattern_" + str(n_pattern) + ".dot"
                if os.path.isfile(pattern_path):
                    pattern_list.append(pattern_path)
                    n_pattern += 1
                else:
                    break

            if os.path.isfile(test_path) and len(pattern_list) > 0:
                expected[n_tests] = expected_list
                test_paths[n_tests] = test_path
                pattern_paths[n_tests] = pattern_list
            else:
                break

            n_tests += 1
        else:
          break

    return n_tests, expected, pattern_paths, test_paths
  

def find_test_dir(args):
    possible_test_dirs = ["tests_graphs", "../tests_graphs"]

    if len(args) > 1:
        possible_test_dirs = [args[1]] + possible_test_dirs

    for path in possible_test_dirs:
        if os.path.isdir(path):
            return path

    return None

main()

