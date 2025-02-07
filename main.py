import logging.handlers
import config
import handler_git
import handler_docker
import handler_docker_class
import handler_compose_stack

from pathlib import Path

import logging

logger = logging.getLogger(config.FEATURE__LOGGING__BASE_NAME)


def setup_logger():
    class ColoredFormatter(logging.Formatter):

        grey = "\x1b[38;20m"
        blue = "\x1b[34;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"
        format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        format_debug = "%(asctime)s - %(levelname)s - %(name)s - {%(filename)s:%(lineno)d} %(message)s"

        FORMATS = {
            logging.DEBUG: grey + format_debug + reset,
            logging.INFO: blue + format + reset,
            logging.WARNING: yellow + format + reset,
            logging.ERROR: red + format + reset,
            logging.CRITICAL: bold_red + format + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    logger.setLevel(logging.DEBUG)

    ##################################################
    # ? console log output
    ##################################################
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(ColoredFormatter())

    logger.addHandler(ch)

    ##################################################
    # ? rotating log file DEBUG
    ##################################################
    rfh = logging.handlers.RotatingFileHandler(
        filename="logs.txt", maxBytes=500_000_000, backupCount=2)
    # fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    rfh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - {%(filename)s:%(lineno)d} - %(message)s'))
    rfh.setLevel(logging.DEBUG)

    logger.addHandler(rfh)

    # fh.setFormatter(CustomFormatter())

    ##################################################
    # ? log file INFO
    ##################################################
    fh = logging.FileHandler(filename="logs-info.txt")
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    fh.setLevel(logging.INFO)

    logger.addHandler(fh)

    ##################################################
    # ? log file CRITICAL
    ##################################################
    fh = logging.FileHandler(filename="logs-critical.txt")
    fh.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    fh.setLevel(logging.ERROR)

    logger.addHandler(fh)

    ##################################################

    # logging.basicConfig(filename="logs.txt",
    #                     filemode='a',
    #                     format='%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s',
    #                     datefmt='%Y-%m-%d %H:%M:%S',
    #                     level=logging.DEBUG)

    logger.info("-"*200)
    logger.info("Stating app")
    logger.info("-"*200)

    logger.debug("test debug")
    logger.info("test info")
    logger.warning("test warning")
    logger.error("test error")
    logger.critical("test critical")


# check config is valid
def validate_config():
    BASE_PATH = Path(__file__).parent.absolute()

    def _validate_path(varname):
        path = getattr(config, varname)
        # print(path)
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

    _validate_value_set("FEATURE__MARK_BAD_STACK", bool)
    _validate_value_set("FEATURE__DEV__WRITE_COMMIT_HASH", bool)
    _validate_value_set("FEATURE__DEV__DRY_RUN_CMDS", bool)


def main():
    setup_logger()
    validate_config()

    changed_files = handler_git.load_git_repo()
    changed_stack_folders = handler_compose_stack.get_updated_stack_folders_v2(
    changed_files)


# print()
# print()
# print()
# print("Start")
    logger.info("Stating stack deployment")

    for folder in changed_stack_folders:
    # print()
    # print(folder.name)
    # print(folder)
    # logger.debug(f"Creating handler for stack {folder.name}")
    # handler_docker.deploy_stack(folder)
    # print()
        handler_c = handler_docker_class.Stack_Handler(folder)
    # print()

    # continue
        try:
            deploy_success = handler_c.deploy_stack()

            if not deploy_success:
                handler_c.logger.info("Deployment success full")
            else:
                handler_c.logger.critical("Failed to deploy due to unknown error")

        except Exception as e:
            handler_c.logger.critical("Failed to deploy due to unhandeld error")
            handler_c.logger.exception("Unhandelded error during deployment")
            print()
            print("-"*100)
            print("ERROR")
            print(e)
            print("-"*100)
        print()
        print()


    logger.info("Script is done")

main()

# TODO then is step 4
