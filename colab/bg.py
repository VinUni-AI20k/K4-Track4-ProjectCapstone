import os, subprocess
s, log = os.environ["BG_SCRIPT"], os.environ["BG_LOG"]
subprocess.Popen(f"setsid nohup bash {s} > {log} 2>&1 &", shell=True)
print("started", s, "->", log)
