#!/bin/bash
. "$(dirname "$0")/_env.sh"
$C ls 2>&1 | tail -5
$C usage 2>&1 | tail -15
