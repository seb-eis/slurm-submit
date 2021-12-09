from typing import Iterable, List, Tuple, Union
import xml.etree.ElementTree as xml
import os
import uuid

from provide import ProviderBase

class JobScript:
    
    def __init__(self, content: str) -> None:
        self.file_path: str = f"./{uuid.uuid4()}.sh"
        self.content: str = content

    def __str__(self) -> str:
        return f"Script:\n{self.content}"
    
    def submit(self, auto_delete: bool = True, submit_format: str = r"sbatch {}") -> None:
        with open(self.file_path, mode= "x") as file: file.write(self.content)
        submit_command = submit_format.format(self.file_path)
        os.system(submit_command)
        if auto_delete: os.remove(self.file_path)

    @classmethod
    def sub_template_var(cls, template: str, var_name: str, data: Union[List[str],str], data_sep: str = "\n") -> str:
        replacement = data if isinstance(data, str) else data_sep.join([x for x in data])
        return template.replace(f"__{var_name}__", replacement)

    @classmethod
    def get_raw_script_template(cls) -> str:
        return "#!/usr/bin/env zsh\n\n__COOKIES__\n\n__COMMANDS__\n\n__MPIEXEC__python3 __CONTROL__ -provide __PROVIDE__ -execute __EXECUTE__ -package __PACKAGE__ -packsize __PACKSIZE__ -args __ARGS__"

    @classmethod
    def get_mpi_replacement(cls, mpisize: int) -> str:
        if mpisize > 1:
            return "$MPIEXEC $FLAGS_MPI_BATCH "
        else:
            return ""

    @classmethod
    def generate_content(cls, execute: str, provide: str, control: str, package_id: int, mpisize: int, packsize: int, cookie_format: str, cookies: List[Tuple[str,str]], commands: List[str], args: List[str]) -> str: 
        template = cls.get_raw_script_template()
        template = cls.sub_template_var(template, "PROVIDE", provide)
        template = cls.sub_template_var(template, "EXECUTE", execute)
        template = cls.sub_template_var(template, "COMMANDS", commands)
        template = cls.sub_template_var(template, "PACKAGE", str(package_id))
        template = cls.sub_template_var(template, "PACKSIZE", str(packsize))
        template = cls.sub_template_var(template, "MPIEXEC", cls.get_mpi_replacement(mpisize))
        template = cls.sub_template_var(template, "COOKIES", [cookie_format.format(x[0], x[1]) for x in cookies])
        template = cls.sub_template_var(template, "ARGS", args, " ")

        # Note: This gives the batch submit system the absolute path to the control script
        template = cls.sub_template_var(template, "CONTROL", os.path.abspath(f"{os.path.dirname(__file__)}/{control}"))
        
        return template

class ArrayJob:

    def __init__(self, template_path: str, submit_args: List[str]) -> None:
        self.template_path: str = template_path
        self.submit_args: List[str] = submit_args
        self.mpi_size: int = 0
        self.mpi_tag: str = ""
        self.provide_script: str = ""
        self.control_script: str = ""
        self.execute_script: str = ""
        self.batch_cookies: List[Tuple[str,str]] = []
        self.cookie_format: str = ""
        self.submit_commands: List[str] = []
        self._load_template_data()

    def __str__(self) -> str:
        return "\n".join(map(lambda x: f"{x[0]:20} -> {x[1]}", self.__dict__.items()))

    def _get_script_data(self, xml_root: xml.Element, element_name: str) -> str:
        node = xml_root.find(element_name)
        if node is None:
            raise Exception(f"The required '{element_name}' node is missing")

        script_path = node.get("Script")
        if script_path is None:
            raise Exception(f"The '{element_name}' script node does not define a 'Script' argument")

        return script_path

    def _get_batch_node(self, xml_root: xml.Element) -> xml.Element:
        node = xml_root.find("Batch")
        if node is None:
            raise Exception("The 'Batch' element is not defined")

        return node

    def _get_cookies_node(self, xml_root: xml.Element) -> xml.Element:
        batch_node = self._get_batch_node(xml_root)

        cookies_node = batch_node.find("Cookies")
        if cookies_node is None:
            raise Exception("The 'Batch' element does not define a'Cookies' element")

        return cookies_node

    def _get_commands_node(self, xml_root: xml.Element) -> xml.Element:
        batch_node = self._get_batch_node(xml_root)

        cmds_node = batch_node.find("Commands")
        if cmds_node is None:
            raise Exception("The 'Btach' element does not define a 'Commands' element")

        return cmds_node

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
            raise Exception("The attribute 'Format' on the 'Cookies' element is not defined")

        return value

    def _get_mpi_tag(self, xml_root: xml.Element) -> str:
        batch_node = self._get_cookies_node(xml_root)
        mpitag = batch_node.get("MpiProcessTag")
        if mpitag is None:
            raise Exception("The 'MpiProcessTag' is not defined. Cannot identify MPI size definition")

        return mpitag

    def _get_mpi_size(self) -> int:
        _, mpival = next(filter(lambda x: x[0] == self.mpi_tag, self.batch_cookies), (self.mpi_tag, "NAN"))
        mpisize = 0
        try: mpisize = int(mpival)
        except: raise Exception(f"The value of the mpi tag ({mpival}) is not an integer")
        if mpisize < 1:
            raise Exception("The set mpi size value must be a non negative integer: n > 0")

        return mpisize

    def _get_submit_commands(self, xml_root: xml.Element) -> List[str]:
        node = self._get_commands_node(xml_root)
        commands = [x.get("Value") for x in node.findall("Command")]
        if any(map(lambda x: x is None, commands)):
            raise Exception("One of the 'Commands' elements has a missing 'Value' attribute")
        
        return commands

    def _load_script_data(self, xml_root: xml.Element) -> None:
        self.control_script = self._get_script_data(xml_root, "Control")
        self.provide_script = self._get_script_data(xml_root, "Provide")
        self.execute_script = self._get_script_data(xml_root, "Execute")

    def _load_batch_data(self, xml_root: xml.Element) -> None:
        self.cookie_format = self._get_batch_cookie_format(xml_root)
        self.batch_cookies = self._get_batch_cookies(xml_root)
        self.submit_commands = self._get_submit_commands(xml_root)
        self.mpi_tag = self._get_mpi_tag(xml_root)
        self.mpi_size = self._get_mpi_size()

    def _load_template_data(self) -> None:
        xml_tree = xml.parse(self.template_path)
        xml_root = xml_tree.getroot()
        self._load_script_data(xml_root)
        self._load_batch_data(xml_root)
        pass

    def overwrite_mpi_size(self, mpi_size: int):
        if mpi_size < 1:
            raise Exception("MPI size overwrite cannot be smaller than 1")
        
        for i in range(0, len(self.batch_cookies)):
            if self.batch_cookies[i][0] == self.mpi_tag:
                self.batch_cookies[i] = (self.mpi_tag, str(mpi_size))

        self.mpi_size = mpi_size

    def generate_script(self, package_id: int, mpi_size_overwrite: Union[int,None] = None) -> JobScript:
        if mpi_size_overwrite is not None and mpi_size_overwrite < 1:
            raise Exception("MPI size override cannot be smaller than 1")

        mpi_size_old = self.mpi_size
        self.overwrite_mpi_size(self.mpi_size if mpi_size_overwrite is None else mpi_size_overwrite)

        script_content = JobScript.generate_content(
            execute=self.execute_script,
            provide=self.provide_script,
            control=self.control_script,
            package_id=package_id,
            mpisize=self.mpi_size,
            packsize=mpi_size_old,
            cookie_format=self.cookie_format,
            cookies=self.batch_cookies,
            commands=self.submit_commands,
            args=self.submit_args)

        self.overwrite_mpi_size(mpi_size_old)
        return JobScript(script_content)

    def generate_all_scripts(self) -> Iterable[JobScript]:
        provider = self.generate_provider()
        count = provider.get_num_of_jobs(self.submit_args)
        package_id = 0
        while count > 0:
            mpi_size = provider.get_mpi_size_by_package_id(self.submit_args, self.mpi_size, package_id)
            yield self.generate_script(package_id, mpi_size)
            package_id += 1
            count -= mpi_size

    def generate_provider(self, cls_name = "Provider") -> ProviderBase: 
        root, _ = os.path.splitext(os.path.expandvars(self.provide_script))
        module = __import__(root)
        return getattr(module, cls_name)(False)
