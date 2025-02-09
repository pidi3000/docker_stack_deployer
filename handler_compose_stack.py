
import config
from pathlib import Path

import logging

####################################################################################################

logger = logging.getLogger(config.FEATURE__LOGGING__BASE_NAME).getChild(__name__)

# logger = logging.getLogger(__name__)

####################################################################################################


def get_all_stack_folders():
    # TODO keep doing what ever I was doin
    # scans the "compose_folder" for possible compose.yaml files

    print(config.COMPOSE_SUBFOLDERS)

    if isinstance(config.COMPOSE_SUBFOLDERS, (list, tuple, set)):
        COMPOSE_FOLDERS = [config.FOLDER_GIT_BASE.joinpath(
            sub_folder) for sub_folder in config.COMPOSE_SUBFOLDERS]
    else:
        COMPOSE_FOLDERS = [config.FOLDER_GIT_BASE.joinpath(
            config.COMPOSE_SUBFOLDERS)]

    services = []

    for folder in COMPOSE_FOLDERS:
        # for path_object in dir.rglob('*/'):
        for path_object in folder.iterdir():
            service_data = None

            if path_object.is_dir():
                # print("Checking...", "\t", path_object)
                try:
                    logger.debug(
                        f"compose yaml file found in path: {path_object}")
                    service_data = _get_service_dir(path_object)

                except FileNotFoundError:
                    # print("No compose yaml file found")
                    logger.debug(
                        f"No compose yaml file found in path: {path_object}")
                    pass

            else:
                continue
                raise TypeError(
                    f"path_object is of unknown type: {type(path_object)}"
                )

            print(service_data)
            print()

            services.append(service_data)

    return services


def _get_service_dir(service_path: Path):

    service_name = service_path.name

    def _get_compose_file():
        # find compose file
        # must either be 'docker-compose.yml' or 'docker-compose.yaml' or '<service name>.yml' or '<service name>.yaml'
        # 'docker-compose.yml' takes priority

        compose_files = [
            "docker-compose.yml",
            "docker-compose.yaml",
            f"{service_name}.yml",
            f"{service_name}.yaml"
        ]

        for file_name in compose_files:
            compose_file = service_path.joinpath(file_name)
            # print(compose_file, compose_file.exists())

            if compose_file.exists():
                return compose_file

        raise FileNotFoundError(
            f"No compose file found in dir: {service_path}"
        )

    def _get_env_file():
        # find .env file
        # must either be '.env' or '<service name>.env'
        # '.env' takes priority

        env_file = service_path.joinpath(".env")
        # print(env_file, env_file.exists())

        if not env_file.exists():
            env_file = service_path.joinpath(f"{service_name}.env")
            # print(env_file, env_file.exists())

            if not env_file.exists():
                env_file = None  # No .env file exists

        return env_file

    {
        "compose_file": _get_compose_file(),
        "env_file": _get_env_file(),
        "service_name": service_name
    }

    return service_path


####################################################################################################

def get_all_stack_folders_v2():
    # scans the "compose_folder" for possible compose.yaml files

    # print(config.COMPOSE_SUBFOLDERS)

    COMPOSE_FOLDERS = [
        config.FOLDER_GIT_BASE.joinpath(sub_folder) for sub_folder in sorted(config.COMPOSE_SUBFOLDERS)
    ]

    stack_folders: list[Path] = []

    # print("Stack folders found:")
    logger.debug(f"Searching for stack folders in git sub-directorys {config.COMPOSE_SUBFOLDERS} :")
    

    for folder in COMPOSE_FOLDERS:
        stack_compose_files = _find_compose_files(folder)
        for compose_file in stack_compose_files:
            s_folder = compose_file.parent
            s_folder_rel = s_folder.relative_to(config.FOLDER_GIT_BASE)

            # print(str(s_folder_rel).ljust(40), "\t", len(s_folder_rel.parts), "\t", s_folder_rel.parts)
            if len(s_folder_rel.parts) >= 2:
                # If path is a sub-directory/not in the top level compose path
                # eg. the path "my_compose_folder/my_app/compose.yaml" is valid
                # but the path "my_compose_folder/compose.yaml" is not valid
                # print(s_folder_rel)
                logger.debug(f"{' '*4}compose sub-folder found: {s_folder_rel}")
                stack_folders.append(s_folder)

    # stack_folders = sorted(stack_folders)

    logger.debug("Finished searching")

    return stack_folders


def _find_compose_files(directory) -> list[Path]:
    """
    Finds all files named "compose.yaml" or "compose.yml" in the given directory and its subdirectories.

    Parameters:
        directory (str or Path): The directory to search in.

    Returns:
        List[Path]: A list of Path objects pointing to the found files.
    """
    directory = Path(directory)  # Ensure the input is a Path object

    if not directory.is_dir():
        raise ValueError(f"The path '{
                         directory}' is not a valid directory.")

    # Search for files matching the patterns
    compose_files = []
    compose_files.extend(list(directory.rglob("compose.yaml")))
    compose_files.extend(list(directory.rglob("compose.yml")))

    return sorted(compose_files)


####################################################################################################
####################################################################################################


def _get_updated_stack_folders_v2(update_files: list[Path, str]):
    # TODO don't remember waht this does, do I still need it?
    # returns folder paths of stacks that have changed files and should be restarted

    all_stack_folders = get_all_stack_folders()

    for change in update_files:
        file_path = change[0]
        if file_path in all_stack_folders:
            pass
####################################################################################################


def get_updated_stack_folders(update_files: list[tuple[Path, str]]) -> list[Path]:
    """Get Path list of stack folders that have changed files

    Parameters
    ----------
    update_files : list[tuple[Path, str]]
        file change list as generated by handler_git.load_git_repo()

    Returns
    -------
    list[Path]
        a list of folders paths containing changed docker stacks
    """
    all_stack_folders = get_all_stack_folders()
    files: list[Path] = [change[0] for change in update_files]

    changed_stack_folders = set()

    # Check if each file is in one of the folders
    for file in files:
        stack_folder = file.parent.absolute()
        if stack_folder in all_stack_folders:
            changed_stack_folders.add(stack_folder)

        # if _is_file_in_folders(file, all_stack_folders):
        #     print(f"{file} is in one of the folders.")
        # else:
        #     print(f"{file} is not in any of the folders.")

    return sorted(changed_stack_folders)


def get_updated_stack_folders_v2(update_files: list[tuple[Path, str]]) -> list[Path]:
    """Get Path list of stack folders that have changed files

    Parameters
    ----------
    update_files : list[tuple[Path, str]]
        file change list as generated by handler_git.load_git_repo()

    Returns
    -------
    list[Path]
        a list of folders paths containing changed docker stacks
    """

    all_stack_folders = get_all_stack_folders_v2()
    changed_stack_folders:set[Path] = set()

    # Check if each file is in one of the folders
    for change in update_files:
        file = change[0]

        stack_folder = _get_folder_containing_file(file, all_stack_folders)
        if stack_folder is not None:
            # print(f"'{file}' is in stack folder '{stack_folder}'")
            changed_stack_folders.add(stack_folder)

        else:
            # print(f"'{file}' is not in any of the folders.")
            pass

    changed_stack_folders = sorted(changed_stack_folders)

    logger.info(f"{'No' if len(changed_stack_folders) < 1 else len(changed_stack_folders)} Stacks found with changed files:")
    
    if len(changed_stack_folders) > 1:
        for changed_stack in changed_stack_folders:
            logger.info(f"{' '*4}{changed_stack.relative_to(config.FOLDER_GIT_BASE)}")
        
    return changed_stack_folders


def _get_folder_containing_file(file_path: Path, folder_list: list[Path]) -> Path | None:
    """Get the folder that contains file referenced by `files_path`

    The returned folder path is one contained in `folder_list`

    Parameters
    ----------
    file_path : Path
        file to searchh for
    folder_list : list[Path]
        folders to search in

    Returns
    -------
    Path | None
        `Path` of the folder containing `file_path`\n
        or `None`
    """
    file_path = Path(file_path)  # Convert file path to Path object

    # Check each folder in the folder_list
    for folder in folder_list:
        folder = Path(folder)
        if file_path.is_relative_to(folder):
            return folder

    return None
