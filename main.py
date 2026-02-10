import logging.handlers
import config
import handler_git
import handler_docker
import handler_docker_class
from handler_docker_class import Stack_Handler
import handler_compose_stack

from pathlib import Path

import logging

# ! TODO add deploy priority


####################################################################################################
# Logging
####################################################################################################

logger = logging.getLogger(config.FEATURE__LOGGING__BASE_NAME)


def setup_logger():
    class MyBaseFormatter(logging.Formatter):
        format_base = "%(asctime)s - %(levelname)-10s - %(name)-40s - %(message)s"
        format_debug = "%(asctime)s - %(levelname)-10s - %(name)-40s - {%(filename)s:%(lineno)d} %(message)s"

        FORMATS = {
            logging.DEBUG:  format_debug,
            logging.INFO: format_base,
            logging.WARNING:  format_base,
            logging.ERROR:  format_base,
            logging.CRITICAL:  format_base
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            formatter = logging.Formatter(log_fmt)
            return formatter.format(record)

    class ColoredFormatter(MyBaseFormatter):

        grey = "\x1b[38;20m"
        blue = "\x1b[34;20m"
        yellow = "\x1b[33;20m"
        red = "\x1b[31;20m"
        bold_red = "\x1b[31;1m"
        reset = "\x1b[0m"

        FORMATS = {
            logging.DEBUG: grey + MyBaseFormatter.format_debug + reset,
            logging.INFO: blue + MyBaseFormatter.format_base + reset,
            logging.WARNING: yellow + MyBaseFormatter.format_base + reset,
            logging.ERROR: red + MyBaseFormatter.format_base + reset,
            logging.CRITICAL: bold_red + MyBaseFormatter.format_base + reset
        }

    logger.setLevel(logging.DEBUG)  # ! DO NOT CHANGE LEVEL HERE
    # ? change level on the appropriate handler (Console or file)

    ##################################################
    # ? console log output
    ##################################################
    logging_level = logging.getLevelNamesMapping().get(config.LOGGING_LEVEL.upper())
    ch = logging.StreamHandler()
    ch.setLevel(logging_level)  # ! <-- change here
    ch.setFormatter(ColoredFormatter())

    logger.addHandler(ch)

    ##################################################
    # ? rotating log file
    ##################################################
    _create_log_file_handler(
        filename="logs.txt",
        log_level=logging_level,  # same level as console output
        backupCount=2,
        # format_string='%(asctime)s - %(levelname)-10s - %(name)s - %(message)s',
        formatter=MyBaseFormatter()
    )

    ##################################################

    logger.info("-"*200)
    logger.info("Starting app")
    logger.info("-"*200)

    logger.debug("test debug")
    logger.info("test info")
    logger.warning("test warning")
    logger.error("test error")
    logger.critical("test critical")


def _create_log_file_handler(filename: str,
                             log_level=logging.DEBUG,
                             format_string: str = '%(asctime)s - %(levelname)-10s - %(name)s - {%(filename)s:%(lineno)d} - %(message)s',
                             formatter: logging.Formatter = None,
                             maxBytes: int = 10_000_000,  # 10MB
                             backupCount: int = 2
                             ):
    """create and attach a file Handler to the main logger

    for entry formatting the `formatter` object is used, if None is provided `format_string` is used to create a simple formatter

    Parameters
    ----------
    filename : str
        _description_
    log_level : _type_, optional
        _description_, by default logging.DEBUG
    format_string : _type_, optional
        _description_, by default '%(asctime)s - %(levelname)-10s - %(name)s - {%(filename)s:%(lineno)d} - %(message)s'
    formatter : logging.Formatter, optional
        _description_, by default None
    maxBytes : int, optional
        _description_, by default 500_000_000
    backupCount : int, optional
        _description_, by default 2
    """

    rfh = logging.handlers.RotatingFileHandler(
        filename=filename,
        maxBytes=maxBytes,
        backupCount=backupCount
    )

    rfh.setFormatter(
        formatter
        if formatter is not None
        else logging.Formatter(format_string)
    )
    rfh.setLevel(log_level)

    logger.addHandler(rfh)

####################################################################################################
# check config is valid
####################################################################################################


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

    # Validate logging level config
    config.LOGGING_LEVEL = config.LOGGING_LEVEL.upper()
    if config.LOGGING_LEVEL not in logging.getLevelNamesMapping():
        raise ValueError(
            f"config.LOGGING_LEVEL must be one of {list(logging.getLevelNamesMapping().keys())}")

####################################################################################################
# run
####################################################################################################


def main():
    validate_config()
    setup_logger()

    changed_files = handler_git.load_git_repo()
    changed_stack_folders = handler_compose_stack.get_updated_stack_folders_v2(
        changed_files)
    # ? list of paths of all compose stacks that have had files changed in the git repo since last check


# print()
# print()
# print()
# print("Start")

    stack_handlers: list[Stack_Handler] = []

    ####################################################################################################
    # ? create stack handler and load deploy info
    ####################################################################################################
    logger.info("Loading stack deploy settings...")
    for folder in changed_stack_folders:
        handler_c = Stack_Handler(folder)
        settings = handler_c.get_deploy_settings(force_reload=True)

        if settings is None:
            continue

        if settings["deploy"] is False:
            continue

        stack_handlers.append(handler_c)

    ##################################################
    # Log deploy queue
    ##################################################
    num_stacks = len(stack_handlers)
    logger.info(f"{num_stacks} Stack{'s' if num_stacks != 1 else ''} queued for deploy:")
    for handler_c in stack_handlers:
        logger.info(f"{' '*4} {handler_c.STACK_FOLDER_BASE}")
        # logger.info(f"{' '*4} {handler_c.STACK_NAME}")

    ##################################################
    # Deploy queued stacks
    ##################################################
    for handler_c in stack_handlers:
        try:
            deploy_success = handler_c.deploy_stack()

            if deploy_success:
                handler_c.logger.info("Deployment successfull")
            else:
                handler_c.logger.critical(
                    "Failed to deploy due to unknown error")

        except Exception as e:
            handler_c.logger.exception("Unhandelded error during deployment")
            handler_c.logger.critical(
                "Failed to deploy due to unhandeld error")

        #     print()
        #     print("-"*100)
        #     print("ERROR")
        #     print(e)
        #     print("-"*100)
        # print()
        # print()

    logger.info("Script is done")


main()
