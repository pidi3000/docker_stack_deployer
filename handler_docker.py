
import re
import yaml
import subprocess
from pathlib import Path

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


##################################################

def run_command(command, stack_folder: Path | None = None):
    """
    Runs a shell command and returns its output.
    """
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


def get_stack_name(stack_folder: Path):
    return stack_folder.name


##################################################

def stop_stack(stack_folder: Path):
    try:
        print(f"stoping down stack {get_stack_name(stack_folder)}...")
        docker_command = f"docker compose stop"
        run_command(docker_command, stack_folder)

    except Exception as e:
        print(f"Failed to stop stack {get_stack_name(stack_folder)}: {str(e)}")


def remove_stack(stack_folder: Path):
    try:
        print(f"Shutting down stack {get_stack_name(stack_folder)}...")
        docker_command = f"docker compose down -v"
        run_command(docker_command, stack_folder)

    except Exception as e:
        print(f"Failed to shut down stack {
              get_stack_name(stack_folder)}: {str(e)}")


##################################################

def start_stack(stack_folder: Path):
    try:
        print(f"staring stack {get_stack_name(stack_folder)}...")
        docker_command = f"docker compose up -d"
        run_command(docker_command, stack_folder)

    except Exception as e:
        print(f"Failed to start stack {
              get_stack_name(stack_folder)}: {str(e)}")


def check_stack_health(stack_folder: Path):
    pass

####################################################################################################


def deploy_stack(stack_folder: Path, is_redeploy: bool = False):

    # ? don't think I need to do anything here?
    # if is_redeploy:
    #     # clear running_stacks folder
    #     # if not stack copy exist in good_stacks folder
    #     #    return with error
    #     #
    #     # copy version to running_stacks
    #     pass

    settings = _load_deploy_settings(stack_folder)

    print(settings)
    if settings is None:
        # TODO add logging
        return

    if "deploy" not in settings or settings["deploy"] is False:
        # TODO add logging
        return

    if "methode" not in settings:
        settings["methode"] = "simple"

    deploy_methode = settings["methode"] if "methode" not in settings else "simple"

    if deploy_methode == "blind":
        _deploy_stack_blind(stack_folder)

    elif deploy_methode == "simple":
        _deploy_stack_simple(stack_folder, is_redeploy)

    elif deploy_methode == "canary":
        pass

    else:
        pass
        # TODO raise error


##################################################


def _deploy_stack_blind(stack_folder: Path):
    # start_stack(stack_folder)
    # TODO

    # clear running_stacks dir
    # copy new version from repo_stacks to running_stacks dir
    # deploy new stack

    pass


def _deploy_stack_simple(stack_folder: Path, is_redeploy: bool = False):
    # if not is_redeploy
    #    check if stack is running and health

    #    if stack is running
    #        if stack is healthy
    #            create stack copy in good_stacks dir

    #     remove stack

    #     **************** same steps as blind deploy ****************
    #     clear running_stacks dir
    #     copy new version from repo_stacks to running_stacks dir
    #     ************************************************************

    # deploy new stack

    # loop for certain time (default could be 30-60 seconds )
    #     if stack is healthy
    #     exit, deploy succesfull (mark deploy is good)

    #     else (stack is not healthy)
    #         wait for 1 second

    # if deploy is NOT good
    #     if is_redeploy
    #         stop stack
    #         raise error

    #     mark stack as bad
    #     remove stack
    #     clear running_stacks dir
    #     copy previous good version from good_stacks to running_stacks dir

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

def _load_deploy_settings(stack_folder: Path):
    setting_files = [
        stack_folder.joinpath("deploy.yaml"),
        stack_folder.joinpath("deploy.yml")
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
        stack_folder.joinpath("compose.yaml"),
        stack_folder.joinpath("compose.yml")
    ]

    for cf in compose_files:
        print(f"check file {cf}")
        if cf.exists() and cf.is_file():
            # try:
            file_string = _extract_deploy_from_compose(cf)
            print(file_string)

            deploy_settings = yaml.safe_load(
                file_string) if file_string else None
            # deploy_settings = yaml.load(sf)

            return deploy_settings
            # except Exception as identifier:
            #     pass

    return None


def _extract_deploy_from_compose(compose_file: Path):
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
