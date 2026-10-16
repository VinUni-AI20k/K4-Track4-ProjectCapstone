#!/bin/bash
# Tải /content/hack/results/* về results/colab/.
. "$(dirname "$0")/_env.sh"
O=$H/results/colab; mkdir -p $O
T=$(mktemp)
echo 'import os; print("\n".join(f for f in os.listdir("/content/hack/results")))' > $T
for f in $($C exec -s $SESS -f $T --timeout 60 2>/dev/null | grep -E '\.(json|csv|mp4|png)$'); do
  timeout 300 $C download -s $SESS /content/hack/results/$f $O/$f 2>&1 | tail -1
done
rm -f $T; ls -la $O
