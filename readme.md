## Description

This is a basic submit and execution system for the SLURM batch workload system that supports slicing and executing huge collections of simulations/jobs as job groups based on MPI. The main use case is to circumvent usually existing limits of for numbers of jobs per user in the queue system, especially annoying for huge sets of short single core or multicore jobs with a fixed number of cores per run.

## Principle

The general batch job configuration, modules to load, and MPI ranks per job group are defined by an XML template. The template further specifies three scripts which are required by the main submit script:

- A provide script that converts the command arguments passed to the submit script into list of list of strings that describe the execution arguments for each individual job. The script further needs to be able to convert the same arguments into a list of execution folders which will be used to run the actual jobs in.
- A control script which is executed by the batch system. It functions as a wrapper that controls the correct provision and startup of each individual program execution based on the package and the MPI rank within the package
- An execution script, which performs or starts the actual work with the command arguments created for that job

## Usage

After configurating your template and writing your provide and execute scripts, the submit system is called using the following command:

```bash
python3 submit.py my_template.xml arg1 arg2 ...
```

Note that both the control and provide script needs to be in the same folder as the main submit script and no directory information can be given in the XML template. The execution script can be located anywhere on your system and should be written into the XML template using an absolute path.