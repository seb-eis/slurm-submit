## How to use?

Copy the contents into the main source folder and replace all placeholders (marked by <>) in them with the correct path information. Then execute the submit system by running the following command:

```bash
python3 submit.py job_mocsim.xml [msl-path] [sequence]
```

The `[msl-path]` is the absolute path to the simulation database and the `[seqeunce]` describes which jobs to start. It supports comma separated values like `1,2,5`, ranges like `1-10`, combinations of both like `1-10,25,22-20` also in the wrong order, and `[Aa]ll` for all jobs found within the database. By default, the submit system detects finished simulations and does not submit the affiliated job indices. The created job folders for the job indices are named as `Job00001,Job00002,...,Job99999`.