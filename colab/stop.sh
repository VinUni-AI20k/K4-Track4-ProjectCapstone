#!/bin/bash
. "$(dirname "$0")/_env.sh"
$C stop -s $SESS 2>&1 | tail -3
$C ls 2>&1 | tail -5
