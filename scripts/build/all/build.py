#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

import atm

def build(file = None):
    # runs the initial assertion for the various commands
    # that are mandatory for execution, this should avoid
    # errors in the middle of the build
    atm.assert_c(("git", "python --version"))

    # starts the build process with the configuration file
    # that was provided to the configuration script
    atm.build(file, arch = "all")

    # retrieves the various values from the global configuration
    # that are going to be used around the configuration
    name_ver = atm.conf("name_ver")
    name_src = atm.conf("name_src")

    # creates the various paths to the folders to be used
    # for the build operation, from the ones already loaded
    repo_f = atm.path("repo")
    result_f = atm.path("result")
    tmp_f = atm.path("tmp")
    dist_f = atm.path("dist")

    # clones the current repository using the git command and then
    # copies the resulting directory to the result and temporary
    # directories, to be used latter in the build
    atm.git(clean = True)
    atm.copy(repo_f, result_f)
    atm.copy(repo_f, os.path.join(tmp_f, name_src))

    # changes the current directory to the repository one and runs
    # the python tests and source build on it, then copies the
    # resulting source build file to the distribution directory
    os.chdir(repo_f)
    atm.pytest()
    atm.pysdist()
    atm.copy(os.path.join("dist", name_ver + ".zip"), dist_f)

    # creates the various hash files for the complete set of files in
    # the distribution directory
    os.chdir(dist_f)
    atm.hash_d()

def run():
    # parses the various arguments provided by the
    # command line and retrieves it defaulting to
    # pre-defined values in case they do not exist
    arguments = atm.parse_args(names = ())
    file = arguments.get("file", None)

    # starts the build process with the parameters
    # retrieved from the current environment
    build(
        file = file
    )

def cleanup():
    atm.cleanup()

if __name__ == "__main__":
    try: run()
    finally: cleanup()
