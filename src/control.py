import sys
import os
import subprocess
from typing import List
from provide import ProviderBase
from mpi4py import MPI

def get_mpi_rank() -> int:
    try:
        return MPI.COMM_WORLD.Get_rank()
    except:
        return 0

def get_control_arg_index(name: str) -> int:
    return sys.argv.index(f"-{name}")

def get_control_arg_value(name: str) -> str:
    index = get_control_arg_index(name)
    return sys.argv[index + 1]

def init_provider(cls_name = "Provider") -> ProviderBase: 
    script_path = get_control_arg_value("provide") 
    root, _ = os.path.splitext(os.path.expandvars(script_path))
    module = __import__(root)
    return getattr(module, cls_name)(True)

def get_package_id() -> int:
    return int(get_control_arg_value("package"))

def get_packsize() -> int:
    return int(get_control_arg_value("packsize"))

def get_control_args() -> List[str]:
    start_index = get_control_arg_index("args") + 1
    return sys.argv[start_index:]

def get_popen_args(mpi_rank: int) -> List[str]:
    provider = init_provider()
    control_args = get_control_args()
    package_id = get_package_id()
    packsize = get_packsize()
    args_list = provider.get_exe_args_by_package_id(control_args, packsize, package_id)
    return args_list[mpi_rank]

def get_script_interpreter(file_name: str) -> str:
    _,ext = os.path.splitext(file_name)
    if ext == ".sh":
        return "bash"
    elif ext == ".ps1":
        return "pwsh"
    elif ext == ".py":
        return "python3"
    else:
        raise Exception(f"The script extension ({ext}) is not supported")


def run_as_subprocess() -> None:
    exe_path = get_control_arg_value("execute")
    interpreter = get_script_interpreter(exe_path)
    mpi_rank = get_mpi_rank()

    # The popen args has the execution path at index 0
    popen_args = get_popen_args(mpi_rank)
    popen_args.insert(0, exe_path)
    popen_args.insert(0, interpreter)
    mpi_info = f"MPI [{(mpi_rank + 1):02d}/ {MPI.COMM_WORLD.Get_size():02d}]"
    print(f"{mpi_info} Executing : {popen_args}", flush=True)
    result = subprocess.run(popen_args)
    print(f"{mpi_info} Returncode: {result.returncode}", flush=True)

run_as_subprocess()
