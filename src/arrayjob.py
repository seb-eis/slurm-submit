from typing import List, Tuple, Union
import xml.etree.ElementTree as xml
import os
import uuid
import re

class JobScript:
    
    file_path: str
    content: str
    auto_delete: bool

    def __init__(self, content: str, auto_delete: bool) -> None:
        self.file_path = f"./{uuid.uuid4()}.sh"
        self.content = content
        self.auto_delete = auto_delete
    
    def submit(self, submit_format: str) -> None:
        with open(self.file_path, mode= "x") as file: file.write(self.content)
        submit_command = submit_format.format(self.file_path)
        os.system(submit_command)
        if self.auto_delete: os.remove(self.file_path)

    @staticmethod
    def sub_template_var(template: str, var_name: str, data: Union[List[str],str], data_sep: str = "\n") -> str:
        replacement = data if isinstance(data, str) else data_sep.join([str(x) for x in data])
        return re.sub(f"__{var_name}__", replacement, template)

    @staticmethod
    def get_raw_script_template() -> str:
        return "#!usr/bin/env zsh\n\n__COOKIES__\n\n__COMMANDS__\n\n__MPIEXEC__ __CONTROL__ -splitter __SPLITTER__ -runner __RUNNER__ -package __PACKAGE__ -args __ARGS__"

    @staticmethod
    def get_mpi_replacement(mpisize: int) -> str:
        if mpisize != 0:
            return "$MPIEXEC $FLAGS_MPI_BATCH"
        else:
            return ""

    @staticmethod
    def generate_content(runner: str, splitter: str, control: str, package: int, mpisize: int, cookie_format: str, cookies: List[Tuple[str,str]], commands: List[str], args: List[str]) -> str:
        template = JobScript.get_raw_script_template()
        template = JobScript.sub_template_var(template, "CONTROL", control)
        template = JobScript.sub_template_var(template, "SPLITTER", splitter)
        template = JobScript.sub_template_var(template, "RUNNER", runner)
        template = JobScript.sub_template_var(template, "COMMANDS", commands)
        template = JobScript.sub_template_var(template, "PACKAGE", str(package))
        template = JobScript.sub_template_var(template, "MPIEXEC", JobScript.get_mpi_replacement(mpisize))
        template = JobScript.sub_template_var(template, "COOKIES", [cookie_format.format(x[0], x[1]) for x in cookies])
        template = JobScript.sub_template_var(template, "ARGS", args)
        return template

class ArrayJob:

    template_path: str
    submit_args: List[str]
    mpi_size: int
    split_script: str
    control_script: str
    run_script: str
    batch_cookies: Tuple[str,str]
    cookie_format: str
    submit_commands: List[str]

    def __init__(self, template_path: str, submit_args: List[str]) -> None:
        self.template_path = template_path
        self.submit_args = submit_args
        self._load_template_data()

    def __str__(self) -> str:
        return "\n".join(map(lambda x: f"{x[0]} -> {x[1]}", self.__dict__.items()))

    def _get_script_data(self, xml_root: xml.Element, element_name: str) -> str:
        node = xml_root.find(element_name)
        if node is None:
            raise Exception(f"The required '{element_name}' node is missing")

        script_path = node.get("Script")
        if script_path is None:
            raise Exception(f"The '{element_name}' script node does not define a 'Script' argument")

        if not os.path.exists(script_path):
            raise Exception(f"The '{element_name}' script '{script_path}' does not exists")

        return script_path

    def _get_cookies_node(self, xml_root: xml.Element) -> xml.Element:
        batch_node = xml_root.find("Batch")
        if batch_node is None:
            raise Exception("The 'Batch' element is not defined")

        cookies_node = batch_node.find("Cookies")
        if cookies_node is None:
            raise Exception("The 'Batch' element does not define a'Cookies' element")

        return cookies_node

    def _get_batch_cookies(self, xml_root: xml.Element) -> List[Tuple[str,str]]:
        node = self._get_cookies_node(xml_root)
        cookies = [(x.get("Tag"), x.get("Value")) for x in node.findall("Cookie")]
        if any(map(lambda x: x[0] is None or x[1] is None, cookies)):
            raise Exception("One of the 'Cookie' elements has a missing 'Tag' or 'Value' attribute")

        return cookies


    def _get_batch_cookie_format(self, xml_root: xml.Element) -> str:
        node = self._get_cookies_node(xml_root)
        value = node.get("Format")
        if value is None:
            raise Exception("The attribute 'Format' on the 'Cookies' element is not defined)

        return value

    def _get_mpi_size(self, xml_root: xml.Element) -> int:
        pass

    def _get_submit_commands(self, xml_root: xml.Element) -> List[str]:
        pass

    def _load_script_data(self, xml_root: xml.Element) -> None:
        self.control_script = self._get_script_data(xml_root, "Control")
        self.split_script = self._get_script_data(xml_root, "Provide")
        self.run_script = self._get_script_data(xml_root, "Execute")

    def _load_batch_data(self, xml_root: xml.Element) -> None:
        self.cookie_format = self._get_batch_cookie_format(xml_root)
        self.batch_cookies = self._get_batch_cookies(xml_root)
        self.submit_commands = self._get_submit_commands(xml_root)
        self.mpi_size = self._get_mpi_size(xml_root)

    def _load_template_data(self) -> None:
        xml_tree = xml.parse(self.template_path)
        xml_root = xml_tree.getroot()
        self._load_script_data(xml_root)
        self._load_batch_data(xml_root)
        pass

    def generate_script(self, package_id: int) -> JobScript:
        pass