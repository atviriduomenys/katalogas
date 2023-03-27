import subprocess
import time

cmd = ["poetry", "run", "python", "manage.py", "migrate"]

proc = subprocess.Popen(
    # Let it ping more times to run longer.
    cmd,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

start_time = time.time()
while True:
    output = proc.stdout.readline()
    if proc.poll() is not None:
        break
    output = proc.stdout.readline()
    if output and "Applying" in output:
        end_time = time.time()
        print(output.strip() + " took {} seconds".format(end_time - start_time))
        start_time = time.time()