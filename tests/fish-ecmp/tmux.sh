#!/bin/sh
set -eu

exe="python3.5 ../../router.py"
exe="../../router.py"

for i in $(seq 1 6) ; do
    tmux split-window -v $exe "127.0.1.$i" 3 "$i.txt" &
    tmux select-layout even-vertical
done
