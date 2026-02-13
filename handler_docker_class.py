
import os
import re
import yaml
import json
import time
import shutil
import subprocess
from pathlib import Path

import logging
import config


#
# Deploy Process:
#
# Notes:
# all service should be able to survive a full compose down
#
#
# ////////////////////////////////////////////////////////////////////////////////////////////////////
# methode "blind":
# script blindly tries to run the cmd "docker compose -f {stack_compose.yaml} up -d".
# no further checks are performed
#
# s
# ////////////////////////////////////////////////////////////////////////////////////////////////////
# ? default
# * "healthcheck" should be configured for each service in the stack
#
# methode "simple":
# script will take the running version down and redeploy the new stack version.
# After deploy a health check is run on all the services,
# if after a certain time (can be changed in deploy options) all services:
#   are "healthy": the script is done.
#   are NOT "healthy": the new stack is taken down and the previous version is redeployed.
#
#
# ////////////////////////////////////////////////////////////////////////////////////////////////////
# ! very experimental
# ! stack can NOT have the "name" property set in compose.yaml
# ! potential conlfict if "container_name" is set
# * "healthcheck" should be configured for each service in the stack
#
# methode "canary":
# script attempts to deploy the stack with a different project name,
# by running the cmd "docker compose -p canary_{stack_name} -f {stack_compose.yaml} up -d".
# Afterwards the script will check on the stacks health,
# if after a certain time all services are healthy the canary and the main deployment are taken down
# and the canary deployment will beome the main deployment.
#
# ////////////////////////////////////////////////////////////////////////////////////////////////////
#

base_logger = logging.getLogger(
    config.FEATURE__LOGGING__BASE_NAME).getChild("Stack_Handler")


class Stack_Handler:

    STACK_FOLDER_BASE: Path
    STACK_FOLDER_GIT: Path
    STACK_FOLDER_RUNNING: Path
    STACK_FOLDER_GOOD: Path

    STACK_NAME: str

    logger: logging.Logger

    _deploy_settings = None

    def __init__(self, stack_folder_base: Path):
        stack_folder_base = stack_folder_base.relative_to(
            config.FOLDER_GIT_BASE)

        self.STACK_NAME = stack_folder_base.name

        self.STACK_FOLDER_BASE = stack_folder_base
        self.STACK_FOLDER_GIT = config.FOLDER_GIT_BASE.joinpath(
            stack_folder_base)
        self.STACK_FOLDER_RUNNING = config.FOLDER_RUNNING_STACK.joinpath(
            stack_folder_base)
        self.STACK_FOLDER_GOOD = config.FOLDER_GOOD_STACK.joinpath(
            stack_folder_base)

        self.logger = base_logger.getChild(self.STACK_NAME)

        self.logger.debug(f"Created handler for stack: {self.STACK_NAME}")
        # self.logger.info(f"{self.STACK_NAME=}")
        self.logger.debug(f"\t{self.STACK_FOLDER_BASE=}")
        self.logger.debug(f"\t{self.STACK_FOLDER_GIT=}")
        self.logger.debug(f"\t{self.STACK_FOLDER_RUNNING=}")
        self.logger.debug(f"\t{self.STACK_FOLDER_GOOD=}")

    ##################################################

    def _run_command(self, command, stack_folder: Path = None):
        """
        Runs a shell command and returns its output.

        stack_folder default =  self.STACK_FOLDER_RUNNING
        """
        if stack_folder is None:
            stack_folder = self.STACK_FOLDER_RUNNING

        # self.logger.debug()
        self.logger.debug(f"running cmd: {command}\nin folder: {stack_folder}")
        # self.logger.debug()
        # self.logger.debug()

        if config.FEATURE__DEV__DRY_RUN_CMDS:
            return True

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=stack_folder
        )

        if result.returncode != 0:
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout

    ####################################################################################################

    ##################################################

    def _stop_compose_stack(self):
        try:
            self.logger.info(f"stoping stack {self.STACK_NAME}...")
            docker_command = f"docker compose stop"
            self._run_command(docker_command)

        except Exception as e:
            self.logger.exception(f"Failed to stop stack {
                self.STACK_NAME}: {str(e)}")

    def _remove_compose_stack(self):
        if self.check_stack_running():

            self.logger.info(
                f"\tShutting down stack..."
            )
            docker_command = f"docker compose down -v"
            self._run_command(docker_command)

            time.sleep(2)

        else:
            self.logger.info(
                f"\tStack is not running, skipping shutdown command"
            )

    ##################################################

    def _start_compose_stack(self):
        try:
            self.logger.info(f"\tstarting stack {self.STACK_NAME}...")
            docker_command = f"docker compose up -d"
            self._run_command(docker_command)

        except Exception as e:
            self.logger.exception(f"Failed to start stack {
                self.STACK_NAME}: {str(e)}")

    ##################################################

    # TODO
    def check_stack_health(self):
        services_health = []
        try:
            self.logger.info(f"checking health of stack {self.STACK_NAME}...")
            docker_command = f"docker compose ps -a --format json"
            data = self._run_command(docker_command)

            info_jsonl = data.split("\n")

            # ? Docker status docs
            # https://docs.docker.com/reference/cli/docker/container/ls/#status

            for jl in info_jsonl:
                service_info = json.loads(jl)
                service_nanme = service_info["Name"]
                service_state = service_info["State"]
                service_health = service_info["Health"]

        except Exception as e:
            self.logger.exception(f"Failed to start stack {
                self.STACK_NAME}: {str(e)}")

    def check_stack_healthy(self) -> bool:
        pass

    def check_stack_running(self) -> bool:
        if self.STACK_FOLDER_RUNNING.exists() and self.STACK_FOLDER_RUNNING.is_dir():
            return True
        else:
            return False

    ####################################################################################################

    def _stack_files_move(self, stack_folder_src: Path, stack_folder_dest: Path):
        # self.logger.debug()
        self.logger.debug(f"copying files \n\tfrom: {
                          stack_folder_src}\n\tto:   {stack_folder_dest}")

        stack_folder_dest.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stack_folder_src, stack_folder_dest,
                        dirs_exist_ok=True)

    def stack_files_load_from_git(self):
        """Copy new stack version from `repo_stacks` to `running_stacks` dir
        """
        self._stack_files_move(
            stack_folder_src=self.STACK_FOLDER_GIT,
            stack_folder_dest=self.STACK_FOLDER_RUNNING
        )

    def stack_files_load_from_good(self):
        self._stack_files_move(
            stack_folder_src=self.STACK_FOLDER_GOOD,
            stack_folder_dest=self.STACK_FOLDER_RUNNING
        )

    def stack_files_save_to_good(self):
        self._stack_files_move(
            stack_folder_src=self.STACK_FOLDER_RUNNING,
            stack_folder_dest=self.STACK_FOLDER_GOOD
        )

    def stack_files_remove_running(self):
        # self.logger.debug()
        self.logger.debug(
            f"removing files \nfrom: {self.STACK_FOLDER_RUNNING}"
        )
        if self.STACK_FOLDER_RUNNING.exists() and self.STACK_FOLDER_RUNNING.is_dir():
            shutil.rmtree(self.STACK_FOLDER_RUNNING)
            # # Loop through all items in the folder
            # for item in self.STACK_FOLDER_RUNNING.iterdir():
            #     if item.is_file():
            #         item.unlink()  # Delete the file
            #     elif item.is_dir():
            #         shutil.rmtree(item)  # Delete the directory and its contents
        self.logger.debug("all files removed")

    ####################################################################################################

    def deploy(self, _is_redeploy: bool = False) -> bool:
        """Run stack auto deploy

        Parameters
        ----------
        _is_redeploy : bool, optional
            used for deploy methodes providing auto re-deploy on error, by default False

        Returns
        -------
        bool
            Deploy success status

        Raises
        ------
        NotImplementedError
            _description_
        NotImplementedError
            _description_
        """

        self.logger.info("Starting stack deployment...")

        deploy_settings = self.get_deploy_settings()

        ####################################################################################################

        if deploy_settings is None or not deploy_settings["deploy"]:
            self.logger.info(f"Skipping deployment for stack: {
                             self.STACK_NAME}")
            return True

        # deploy_stack: bool = deploy_settings["deploy"]

        # TODO clean this up
        # deploy_methode = settings["methode"] if "methode" not in settings else "blind"
        deploy_methode = deploy_settings["methode"]

        try:
            if deploy_methode == "blind":
                self._deploy_stack_blind()
                return True

            elif deploy_methode == "simple":
                # return False
                raise NotImplementedError(
                    "the `simple` deployment methode has not been implemented yet")

                self._deploy_stack_simple(_is_redeploy)

            elif deploy_methode == "canary":
                # return False
                raise NotImplementedError(
                    "the `canary` deployment methode has not been implemented yet")

            else:
                # TODO raise error
                raise ValueError(
                    f"Invalid deployment methode: {deploy_methode}")

        except Exception as e:
            self.logger.exception(
                f"Stack deployment failed: {self.STACK_NAME}: {str(e)}"
            )

    def remove(self):
        self.logger.info("Removing stack...")

        self._remove_compose_stack()
        self.logger.info(
            f"\tRemoving stack files"
        )
        self.stack_files_remove_running()

        return True

    ##################################################

    def _deploy_stack_blind(self):
        self._remove_compose_stack()
        self.logger.info(f"\tloading new stack version from git...")
        self.stack_files_remove_running()
        self.stack_files_load_from_git()
        self._start_compose_stack()

    def _deploy_stack_simple(self, is_redeploy: bool = False):

        # if not is_redeploy
        if not is_redeploy:
            #    if stack is running
            if self.check_stack_running():
                #        if stack is healthy
                if self.check_stack_healthy():
                    #            create stack copy in good_stacks dir
                    self.stack_files_save_to_good()

        # **************** similar steps as blind deploy ****************
        # remove stack
        # clear running_stacks dir
        # copy new version from repo_stacks to running_stacks dir
        # deploy new stack
        # ************************************************************

        self._remove_compose_stack()
        self.stack_files_remove_running()
        if is_redeploy:
            self.stack_files_load_from_good()
        else:
            self.stack_files_load_from_git()
        self._start_compose_stack()

        time_start = time.time()
        deploy_good = False

        while time.time() - time_start < config.STACK_HEALTHCHECK_TIMEOUT:
            if self.check_stack_healthy():
                deploy_good = True
                break

            else:
                time.sleep(1)

        # if deploy is NOT good
        if not deploy_good:
            #     if is_redeploy
            if is_redeploy:
                self._stop_compose_stack()
                # ! send notification about failed redeploy
                raise RuntimeError("Stack Redeploy failed")
                # TODO raise good error

            # ! send notification about failed deploy
            # ! doesn't work like this because the previous version could have been using a different deploy methode
            self._deploy_stack_simple(is_redeploy=True)

            # TODO future mark stack as bad, do this after redeploy to be sure it's not an external error
            #  if code reaches this point, the redeploy was succesfull, if not an error would have been raised in the previous step

        # ? deploy is good
        else:
            if is_redeploy:
                # ! send notification about succesfull redeploy
                pass
            else:
                # ! send notification about succesfull deploy
                pass
            pass

            #    ? not sure if there is more to do here ?
        pass

    ####################################################################################################

    def get_deploy_settings(self, validate_settings: bool = True, force_reload: bool = False):
        self.logger.debug(f"Loading deploy settings")
        self.logger.debug(f"\t{self._deploy_settings=}")
        self.logger.debug(f"\t{force_reload=}")

        if self._deploy_settings is not None and not force_reload:
            return self._deploy_settings

        deploy_settings = self._load_deploy_settings()
        self.logger.debug(f"{deploy_settings=}")

        if not validate_settings:
            self._deploy_settings = deploy_settings
            return self._deploy_settings

        # ! validate deploy settings are correct
        if deploy_settings is None:
            # TODO add logging
            self.logger.debug(f"Could not load any deploy settings")
            self._deploy_settings = deploy_settings
            return self._deploy_settings
            # raise TypeError(f"Could not load any deploy settings")

        # Validate "deploy"
        if "deploy" not in deploy_settings or not isinstance(deploy_settings["deploy"], bool):
            # TODO add logging
            self.logger.warning(
                f"parameter `deploy` is not set or not of type `bool`")
            # raise ValueError(
            #     f"parameter `deploy` is not set or not of type `bool`")

        # Validate "methode"
        if "methode" not in deploy_settings or not isinstance(deploy_settings["methode"], str):
            # TODO add logging
            self.logger.warning(
                f"parameter `methode` is not set or not of type `str`")
            # raise ValueError(
            #     f"parameter `methode` is not set or not of type `str`")

        if str(deploy_settings["methode"]).lower() not in ["blind", "simple", "canary"]:
            # TODO add logging
            self.logger.warning(
                f"Value of parameter `methode` is invalid, must be one of: 'blind', 'simple', 'canary'")
            # raise ValueError(f"parameter `methode` is not set")

        self.logger.debug(f"Deploy settings loaded and validated successfully")
        self._deploy_settings = deploy_settings
        return self._deploy_settings

    def _load_deploy_settings(self):
        setting_files = [
            self.STACK_FOLDER_GIT.joinpath("deploy.yaml"),
            self.STACK_FOLDER_GIT.joinpath("deploy.yml")
        ]

        deploy_settings = None

        for sf in setting_files:
            self.logger.debug(f"\tcheck file {sf}")
            if sf.exists() and sf.is_file():
                self.logger.debug(
                    f"\tloading settings from deploy file '{sf}'")

                with open(sf, "r") as f:
                    deploy_settings = yaml.safe_load(f)
                    # deploy_settings = yaml.load(sf)

                return deploy_settings
                # ! --------------------------------------------------
                break

            else:
                self.logger.debug(f"\tdeploy file not found")

        self.logger.debug(
            f"\tno deploy settings file found, attempting to extract settings from compose file")
        return self._extract_deploy_from_compose()

    def _extract_deploy_from_compose(self):
        """
        Extracts and returns the text within the block marked by 
        '# Deploy Start #' and '# Deploy End #' using regex.

        :param file_path: Path to the text file.
        :return: String containing the text within the deploy block, 
                or None if the block is not found.
        """

        compose_files = [
            self.STACK_FOLDER_GIT.joinpath("compose.yaml"),
            self.STACK_FOLDER_GIT.joinpath("compose.yml")
        ]

        def _extract_settings_from_file(compose_file: Path):
            try:
                with open(compose_file, 'r') as file:
                    file_content = file.read()

                # Regex to match the block between the markers
                match = re.search(
                    r"# Deploy Start #\n(.*?)\n# Deploy End #", file_content, re.DOTALL)

                if match:
                    data = match.group(1)

                    data = "\n".join(
                        line.removeprefix("#").strip() for line in data.split("\n")
                    )

                    return data
                else:
                    return None  # Return None if no block is found

            except FileNotFoundError:
                self.logger.exception(
                    f"Error: File not found at {compose_file}")
                return None
            except Exception as e:
                self.logger.exception(f"An error occurred: {e}")
                return None

        for cf in compose_files:
            self.logger.debug(f"\tcheck file {cf}")
            if cf.exists() and cf.is_file():
                self.logger.debug(
                    f"\tloading settings from compose file '{cf}'")

                file_string = _extract_settings_from_file(cf)

                deploy_settings = yaml.safe_load(
                    file_string) if file_string else None

                # self.logger.debug(f"{deploy_settings=}")

                # deploy_settings = yaml.load(sf)

                return deploy_settings

            else:
                self.logger.debug(f"\tcompose file '{cf}' not found")

        self.logger.debug(
            f"could not load any delploy settings for stack {self.STACK_NAME}")
