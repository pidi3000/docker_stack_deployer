from pathlib import Path


####################################################################################################
# Fodlers
####################################################################################################
COMPOSE_SUBFOLDERS = [
    "git_subfolder"
]
""" Folder to search for docker compose stacks"""

PATH_FOLDER_BASE = Path("/home/user/docker_stack_deployer_data")
""" Base folder for all data used by the script, ouside of script folder for persistent storage. This is where the git repo will be cloned, and where the stack files will be stored"""

PATH_FOLDER_GIT_BASE = PATH_FOLDER_BASE.joinpath("git_base")
""" Folder of the cloned git repo"""

PATH_FOLDER_RUNNING_STACK = PATH_FOLDER_BASE.joinpath("stack_running")
""" Folder containing all files for currently running stack version"""

PATH_FOLDER_GOOD_STACK = PATH_FOLDER_BASE.joinpath("stack_good")
""" Folder containing stack files for last known good stack version """

PATH_FILE_COMMIT_HASH = PATH_FOLDER_BASE.joinpath("last_commit_hash.txt")
""" File to store the last commit hash, used to detect changes in the git repo"""


####################################################################################################
# LOGGING
####################################################################################################
LOGGING_LEVEL = "info"
LOGGING_FILE_PATH = "logs.txt"

####################################################################################################
# Feature flags
####################################################################################################

FEATURE__LOGGING__BASE_NAME = "app"

FEATURE__MARK_BAD_STACK = False  # ! not used yet
FEATURE__DEV__WRITE_COMMIT_HASH = True
# commands are not actually run, and only print to console
FEATURE__DEV__DRY_RUN_CMDS = True


##################################################
# Helth check
##################################################

STACK_HEALTHCHECK_TIMEOUT = 90  # TODO make this available in deploy settings file

####################################################################################################
# GIT
####################################################################################################

GIT_URL = ""
GIT_USER = ""
# TODO load this from a file
GIT_PASS = ""
# TODO for now this only works on first clone, following pulls will use the branch used by the original clone
GIT_BRANCH = "main"
