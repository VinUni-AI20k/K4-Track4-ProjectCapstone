#!/bin/bash
. "$(dirname "$0")/_env.sh"
timeout 150 $C exec -s $SESS -f $H/colab/tail.py --timeout 60 --env "CMD=tail -n ${N:-30} $LOG" 2>&1 | tail -n $(( ${N:-30} + 5 ))
