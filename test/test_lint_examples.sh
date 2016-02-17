#!/bin/bash
# DEPRECATED: this can be done without the script in the Makefile
for f in `ls ../examples/`; do pylint -E $f; done
