import config
import handler_git
import handler_docker
import handler_docker_class
import handler_compose_stack

from pathlib import Path


# check config is valid
def validate_config():
    BASE_PATH = Path(__file__).parent.absolute()

    def _validate_path(varname):
        path = getattr(config, varname)
        print(path)
        try:
            path = Path(path)
        except TypeError:
            raise TypeError(
                f"'config.{varname}' must be convertable to a `pathlib.Path` object")

        if not path.is_relative_to(BASE_PATH):
            raise ValueError(f"the path 'config.{
                             varname}' must inside script base path ('{BASE_PATH}')")

    def _validate_value_set(varname, var_type):

        if not hasattr(config, varname):
            raise ValueError(f"config.{varname} is not set")

        if not isinstance(getattr(config, varname), var_type):
            raise TypeError(f"config.{varname} is not of type {var_type}")

    ####################################################################################################

    # if not isinstance(config.COMPOSE_SUBFOLDERS, list):
    #     raise TypeError("config.COMPOSE_SUBFOLDERS must be of type list")

    _validate_path("FOLDER_GIT_BASE")
    _validate_path("FOLDER_RUNNING_STACK")
    _validate_path("FOLDER_GOOD_STACK")

    _validate_value_set("GIT_URL", str)
    _validate_value_set("GIT_USER", str)
    _validate_value_set("GIT_PASS", str)

    _validate_value_set("COMPOSE_SUBFOLDERS", (list, tuple, set))
    # config.COMPOSE_SUBFOLDERS = [config.FOLDER_GIT_BASE.joinpath(
    #     sub_folder) for sub_folder in config.COMPOSE_SUBFOLDERS]


validate_config()

changed_files = handler_git.load_git_repo()
changed_stack_folders = handler_compose_stack.get_updated_stack_folders_v2(changed_files)

# print()
# print()
# print()
print("Start")
for folder in changed_stack_folders:
    print()
    print(folder.name)
    print(folder)
    #handler_docker.deploy_stack(folder)
    print()
    handler_c = handler_docker_class.Stack_Handler(folder)
    print()
    handler_c.deploy_stack()
    print()
    print()
    



# TODO then is step 4
# TODO when performing an action on a stack, I have to cd into the stack folder and then run a docker cmd