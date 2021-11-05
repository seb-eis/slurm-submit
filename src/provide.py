from abc import abstractmethod
from typing import List

class Provider:

    @abstractmethod
    def get_job_argument_list(self, control_args: List[str]) -> List[List[str]]:
        """
        Converts the List[str] arguments passed to the submit system into a List[List[str]] where each List[str]
        is the set of arguments for the actual job runner script
        """

    @abstractmethod
    def get_job_execution_paths(self, control_args: List[str]) -> List[str]:
        """
        Converts the List[str] arguments passed to the submit system into a List[str] where each entry is the
        execution path of the job runner at that job index
        """

    def get_num_of_jobs(self, control_args: List[str]) -> int:
        """
        Get the total number of jobs that is defined by the control argument list
        """
        return len(self.get_job_argument_list(control_args))