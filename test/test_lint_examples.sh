#!/bin/bash
for f in `ls ../examples/`; do pylint -E $f; done
