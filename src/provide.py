from abc import abstractmethod
from typing import List

class ProviderBase:

    """
    Base class for all providers that convert a set of submit arguments into a List[List[str]] that describe the execution args for all individual jobs
    """

    def __init__(self, is_silent: bool) -> None:
        self.is_silent = is_silent

    @abstractmethod
    def get_all_execution_args(self, control_args: List[str]) -> List[List[str]]:
        """
        Converts the List[str] arguments passed to the submit system into a List[List[str]] where each List[str]
        is the set of arguments for the actual job runner script
        """

    @abstractmethod
    def get_all_execution_paths(self, control_args: List[str]) -> List[str]:
        """
        Converts the List[str] arguments passed to the submit system into a List[str] where each entry is the
        execution path of the job runner at that job index
        """

    def get_exe_args_by_package_id(self, control_args: List[str], max_mpi_size: int, package_id: int) -> List[List[str]]:
        """
        Converts the List[str] arguments passed to the submit system into a List[List[str]] where each List[str]
        is the set of arguments for the actual job runner script. Returns only the part of the list required
        for the current job package and prepends the execution path
        """

        if max_mpi_size < 1 or package_id < 0:
            raise Exception(f"The maximum mpisize ({max_mpi_size}) or the package id ({package_id}) is invalid!")

        execution_args = self.get_all_execution_args(control_args)
        execution_paths = self.get_all_execution_paths(control_args)

        if len(execution_args) != len(execution_paths):
            raise Exception("The length of the execution arguments and execution paths has to be equal")

        total_job_count = len(execution_paths)
        min_id = package_id * max_mpi_size
        max_id = min((package_id + 1) * max_mpi_size, total_job_count)

        if max_id == min_id:
            raise Exception("The minimal job id is equal to the maximum job id")

        execution_args_part = execution_args[min_id:max_id]
        for i, path in zip(range(0, len(execution_paths)), execution_paths[min_id:max_id]):
            execution_args_part[i].insert(0, path)

        return execution_args_part

        
    def get_mpi_size_by_package_id(self, control_args: List[str], max_mpi_size: int, package_id: int) -> int:
        """
        Get the number of MPI ranks required for a specific package id and max number of MPI ranks per job
        """
        return len(self.get_exe_args_by_package_id(control_args, max_mpi_size, package_id))
    
    def get_num_of_jobs(self, control_args: List[str]) -> int:
        """
        Get the total number of jobs that is defined by the control argument list
        """
        return len(self.get_all_execution_paths(control_args))

class Provider(ProviderBase):
    """
    A test provider that supplies a certain number of test arguments
    """
    
    def __init__(self, is_silent: bool) -> None:
        super().__init__(is_silent)

    def get_all_execution_args(self, control_args: List[str]) -> List[List[str]]:
        return [control_args.copy() for _ in self.get_range()]

    def get_all_execution_paths(self, control_args: List[str]) -> List[str]:
        return [f"./Job{x:05d}" for x in self.get_range()]

    def get_range(self):
        return range(1, 201)