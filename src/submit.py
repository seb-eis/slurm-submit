import arrayjob
import sys

print(f"Submit script called with args: {sys.argv[1:]}")

job = arrayjob.ArrayJob(sys.argv[1], sys.argv[2:])
for script in job.generate_all_scripts():
    script.submit(auto_delete=True)