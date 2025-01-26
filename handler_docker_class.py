
import os
import re
import yaml
import json
import time
import shutil
import subprocess
from pathlib import Path

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


class Stack_Handler:

    STACK_FOLDER_BASE: Path
    STACK_FOLDER_GIT: Path
    STACK_FOLDER_RUNNING: Path
    STACK_FOLDER_GOOD: Path

    STACK_NAME: str

    def __init__(self, stack_folder_base: Path):
        stack_folder_base = stack_folder_base.relative_to(
            config.FOLDER_GIT_BASE)

        self.STACK_FOLDER_BASE = stack_folder_base
        self.STACK_FOLDER_GIT = config.FOLDER_GIT_BASE.joinpath(
            stack_folder_base)
        self.STACK_FOLDER_RUNNING = config.FOLDER_RUNNING_STACK.joinpath(
            stack_folder_base)
        self.STACK_FOLDER_GOOD = config.FOLDER_GOOD_STACK.joinpath(
            stack_folder_base)

        self.STACK_NAME = stack_folder_base.name

        print(f"{self.STACK_FOLDER_BASE=}")
        print(f"{self.STACK_FOLDER_GIT=}")
        print(f"{self.STACK_FOLDER_RUNNING=}")
        print(f"{self.STACK_FOLDER_GOOD=}")
        print(f"{self.STACK_NAME=}")

    ##################################################

    def run_command(self, command, stack_folder: Path = None):
        """
        Runs a shell command and returns its output.

        stack_folder default =  self.STACK_FOLDER_RUNNING
        """
        if stack_folder is None:
            stack_folder = self.STACK_FOLDER_RUNNING

        print()
        print(f"running cmd: {command}\nin folder: {stack_folder}")
        print()
        print()
        return True

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=stack_foldert
        )

        if result.returncode != 0:
            raise Exception(f"Command failed: {result.stderr}")
        return result.stdout

    ####################################################################################################

    ##################################################

    def stop_stack(self):
        try:
            print(f"stoping down stack {self.STACK_NAME}...")
            docker_command = f"docker compose stop"
            self.run_command(docker_command)

        except Exception as e:
            print(f"Failed to stop stack {
                  self.STACK_NAME}: {str(e)}")

    def remove_stack(self):
        try:
            print(f"Shutting down stack {
                  self.STACK_NAME}...")
            docker_command = f"docker compose down -v"
            self.run_command(docker_command)

        except Exception as e:
            print(f"Failed to shut down stack {
                self.STACK_NAME}: {str(e)}")

    ##################################################

    def start_stack(self):
        try:
            print(f"staring stack {self.STACK_NAME}...")
            docker_command = f"docker compose up -d"
            self.run_command(docker_command)

        except Exception as e:
            print(f"Failed to start stack {
                self.STACK_NAME}: {str(e)}")

    ##################################################

    def check_stack_health(self):
        services_health = []
        try:
            print(f"checking health of stack {self.STACK_NAME}...")
            docker_command = f"docker compose ps -a --format json"
            data = self.run_command(docker_command)

            info_jsonl = data.split("\n")
            
            # ? Docker status docs
            # https://docs.docker.com/reference/cli/docker/container/ls/#status

            for jl in info_jsonl:
                service_info = json.loads(jl)
                service_nanme = service_info["Name"]
                service_state = service_info["State"]
                service_health = service_info["Health"]

        except Exception as e:
            print(f"Failed to start stack {
                self.STACK_NAME}: {str(e)}")

    def check_stack_healthy(self) -> bool:
        pass

    def check_stack_running(self) -> bool:
        pass

    ####################################################################################################

    def _stack_files_move(self, stack_folder_src: Path, stack_folder_dest: Path):
        print()
        print(f"copying files \nfrom: {
              stack_folder_src}\nto:   {stack_folder_dest}")

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
        print()
        print(f"removing files \nfrom: {self.STACK_FOLDER_RUNNING}")
        if self.STACK_FOLDER_RUNNING.exists() and self.STACK_FOLDER_RUNNING.is_dir():
            shutil.rmtree(self.STACK_FOLDER_RUNNING)
            # # Loop through all items in the folder
            # for item in self.STACK_FOLDER_RUNNING.iterdir():
            #     if item.is_file():
            #         item.unlink()  # Delete the file
            #     elif item.is_dir():
            #         shutil.rmtree(item)  # Delete the directory and its contents
        print("all files removed")

    ####################################################################################################

    def deploy_stack(self, is_redeploy: bool = False):

        # ? don't think I need to do anything here?
        # * this will be handle by each deploy methode
        # if is_redeploy:
        #     # clear running_stacks folder
        #     # if not stack copy exist in good_stacks folder
        #     #    return with error
        #     #
        #     # copy good version to running_stacks
        #     pass
        # ***********************************************************

        settings = self._load_deploy_settings()

        print(settings)
        if settings is None:
            # TODO add logging
            return

        if "deploy" not in settings or settings["deploy"] is False:
            # TODO add logging
            return

        if "methode" not in settings:
            settings["methode"] = "blind"

        # TODO clean this up
        # deploy_methode = settings["methode"] if "methode" not in settings else "blind"
        deploy_methode = settings["methode"]

        if deploy_methode == "blind":
            self._deploy_stack_blind()

        elif deploy_methode == "simple":
            raise NotImplementedError(
                "the ´simple´ deployment methode has not been implemented yet")

            self._deploy_stack_simple(is_redeploy)

        elif deploy_methode == "canary":
            raise NotImplementedError(
                "the ´canary´ deployment methode has not been implemented yet")

        else:
            pass
            # TODO raise error

    ##################################################

    def _deploy_stack_blind(self):
        self.remove_stack()
        self.stack_files_remove_running()
        self.stack_files_load_from_git()
        self.start_stack()

    def _deploy_stack_simple(self, is_redeploy: bool = False):

        # if not is_redeploy
        if not is_redeploy:
            #    if stack is running
            if self.check_stack_running():
                #        if stack is healthy
                if self.check_stack_healthy():
                    #            create stack copy in good_stacks dir
                    self.stack_files_save_to_good()

        # **************** same steps as blind deploy ****************
        # remove stack
        # clear running_stacks dir
        # copy new version from repo_stacks to running_stacks dir
        # deploy new stack
        # ************************************************************

        self.remove_stack()
        self.stack_files_remove_running()
        self.stack_files_load_from_git()
        self.start_stack()

        time_start = time.time()
        deploy_good = False

        while time.time() - time_start < config.STACK_HEALTHCHECK_TIMEOUT:
            if self.check_stack_healthy():
                deploy_good = True
                break

            else:
                time.sleep

        # if deploy is NOT good
        if not deploy_good:
            #     if is_redeploy
            if is_redeploy:
                self.stop_stack()
                raise RuntimeError("Stack Redeploy failed")
                # TODO raise good error

        #     TODO future mark stack as bad
        #     remove stack
            self.remove_stack()
            self.stack_files_remove_running()
            self.stack_files_load_from_good()
            self.start_stack()

            # ! TODO continue on this
        #     run `deploy_stack` with flag `is_redeploy` == True

        #     if deploy is NOT good
        #         stop stack
        #         raise error

        #     if deploy IS good
        #         send notification

        # if deploy IS good
        #    yeppiee ?
        #    ? not sure if there is more to do here ?

        pass

    ####################################################################################################

    def _load_deploy_settings(self):
        setting_files = [
            self.STACK_FOLDER_GIT.joinpath("deploy.yaml"),
            self.STACK_FOLDER_GIT.joinpath("deploy.yml")
        ]

        deploy_settings = None

        for sf in setting_files:
            print(f"check file {sf}")
            if sf.exists() and sf.is_file():
                with open(sf, "r") as f:
                    deploy_settings = yaml.safe_load(f)
                    # deploy_settings = yaml.load(sf)

                return deploy_settings
                # ! --------------------------------------------------
                break

        compose_files = [
            self.STACK_FOLDER_GIT.joinpath("compose.yaml"),
            self.STACK_FOLDER_GIT.joinpath("compose.yml")
        ]

        for cf in compose_files:
            print(f"check file {cf}")
            if cf.exists() and cf.is_file():
                # try:
                file_string = self._extract_deploy_from_compose(cf)
                print(file_string)

                deploy_settings = yaml.safe_load(
                    file_string) if file_string else None
                # deploy_settings = yaml.load(sf)

                return deploy_settings
                # except Exception as identifier:
                #     pass

        return None

    def _extract_deploy_from_compose(self, compose_file: Path):
        """
        Extracts and returns the text within the block marked by 
        '# Deploy Start #' and '# Deploy End #' using regex.

        :param file_path: Path to the text file.
        :return: String containing the text within the deploy block, 
                or None if the block is not found.
        """
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
            print(f"Error: File not found at {compose_file}")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
