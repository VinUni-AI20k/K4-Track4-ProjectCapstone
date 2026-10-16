import os, subprocess
print(subprocess.run(os.environ.get("CMD", "tail -n 15 /content/*.log"), shell=True, capture_output=True, text=True, executable="/bin/bash").stdout[-6000:])
