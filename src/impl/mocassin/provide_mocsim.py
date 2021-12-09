from typing import Dict, List, Tuple
from provide import ProviderBase
import os
import sqlite3
import re

class Provider(ProviderBase):

    def __init__(self, is_silent: bool) -> None:
        super().__init__(is_silent)
        self.incomplete_job_indices: Dict[str,List[int]] = dict()

    def get_all_execution_args(self, control_args: List[str]) -> List[List[str]]:
        msl_path, job_info = self.get_msl_and_job_info(control_args)
        raw_job_indices = self.convert_job_info_to_indices(msl_path, job_info)
        job_indices = self.get_indices_without_completed_jobs(raw_job_indices)
        pwd = os.path.abspath(os.path.curdir)

        exe_args: List[List[str]] = []
        for job_index in job_indices:
            path = self.ensure_job_path_created(pwd, job_index)
            args = self.get_startup_args_by_job_index(msl_path, path, job_index)
            exe_args.append(args)

        return exe_args

    def get_all_execution_paths(self, control_args: List[str]) -> List[str]:
        msl_path, job_info = self.get_msl_and_job_info(control_args)
        raw_job_indices = self.convert_job_info_to_indices(msl_path, job_info)
        job_indices = self.get_indices_without_completed_jobs(raw_job_indices)
        pwd = os.path.abspath(os.path.curdir)

        job_paths = []
        for job_index in job_indices:
            job_path = self.ensure_job_path_created(pwd, job_index)
            job_paths.append(job_path)

        return job_paths

    def ensure_job_path_created(self, pwd: str, job_index: int) -> str:
        path = f"{pwd}/Job{job_index:05d}"
        if not os.path.exists(path):
            os.mkdir(path)

        return path

    def throw_if_invalid_arg_count(self, control_args: List[str]) -> None:
        if len(control_args) != 2:
            raise Exception("The provider scripts expects two control arguments")

    def get_msl_and_job_info(self, control_args: List[str]) -> Tuple[str,str]:
        self.throw_if_invalid_arg_count(control_args)
        path = self.get_msl_path(control_args)
        jobs = self.get_job_info(control_args)
        return path, jobs
    
    def get_msl_path(self, control_args: List[str]) -> str:
        for arg in control_args:
            if ".msl" in arg:
                return arg

        raise Exception("The control arguments do not supply an '.msl' file path")

    def get_job_info(self, control_args: List[str]) -> str:
        for arg in control_args:
            if ".msl" not in arg:
                return arg

    def convert_job_info_to_indices(self, msl_path: str, job_info: str) -> List[int]:
        if job_info == "All" or job_info == "all":
            return self.load_all_job_indices_from_db(msl_path)
        
        single_re = re.compile(r"(?<![0-9\-])([0-9]+)(?![0-9\-])")
        ranged_re = re.compile(r"([0-9]+)-([0-9]+)")
        values = []
        for match in single_re.finditer(job_info):
            values.append(int(match.group(1)))

        for match in ranged_re.finditer(job_info):
            min_value = min(int(match.group(1)), int(match.group(2)))
            max_value = max(int(match.group(1)), int(match.group(2))) + 1
            values.extend([i for i in range(min_value, max_value)])

        return sorted(set(values))

    def convert_indices_to_job_info(self, indices: List[int]) -> str:
        if len(indices) == 0:
            return ""
        if len(indices) == 1:
            return str(indices[0])

        result = ""
        id_0 = indices[0]
        id_1 = indices[0]
        for i in indices[1:]:
            if i == (id_1 + 1):
                id_1 = i
                if id_1 != indices[-1]:
                    continue
            if id_0 == id_1:
                result = result + ("," if result != "" else "") + str(id_0)
            else:
                result = result + ("," if result != "" else "") + str(id_0) + "-" + str(id_1)
            if id_1 != i and i == indices[-1]:
                result = result + ("," if result != "" else "") + str(i)
            id_0 = id_1 = i

        return result

    def get_indices_without_completed_jobs(self, indices: List[int]) -> List[int]:
        job_info = self.convert_indices_to_job_info(indices)
        if self.incomplete_job_indices.get(job_info) is None:   
            pwd = os.path.abspath(os.path.curdir)
            unfinished = []
            finished = []
            for i in indices:
                dir_path = self.ensure_job_path_created(pwd, i)
                stdout_path = f"{dir_path}/stdout.log"

                if not os.path.exists(stdout_path):
                    unfinished.append(i)
                    continue

                with open(stdout_path) as file:
                    if "ABORT_REASON" not in file.read():
                        unfinished.append(i)
                        continue
                finished.append(i)

            self.incomplete_job_indices[job_info] = unfinished
            unfinished_job_info = self.convert_indices_to_job_info(unfinished)
            finished_job_info = self.convert_indices_to_job_info(finished)
            if not self.is_silent:
                print(f"PROVIDER-INFO: The system detected ({finished_job_info}) as finished and ({unfinished_job_info}) as unfinished simulations.")
                print(f"PROVIDER-INFO: Only unfinished simulations will be started.")
        
        return self.incomplete_job_indices[job_info]

    def load_all_job_indices_from_db(self, msl_path: str) -> List[int]:
        with sqlite3.connect(msl_path) as db:
            raw = db.cursor().execute("select Id from JobModels order by Id").fetchall()
            return [int(x[0]) for x in raw]

    def get_startup_args_by_job_index(self, msl_path: str, job_path: str, job_index: int) -> List[str]:
        return ["-jobId", str(job_index), "-dbPath", os.path.abspath(msl_path), "-ioPath", os.path.abspath(job_path), "-stdout", "stdout.log"]