#!/bin/bash
./plan.py blind 'run_hanoi("samples/hanoi4_fc2/","fc2",import_module("puzzles.hanoi"),4)' |& tee $(dirname $0)/blind-hanoi4.log