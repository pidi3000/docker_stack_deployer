from pathlib import Path

####################################################################################################
####################################################################################################


####################################################################################################
# Fodlers
####################################################################################################
COMPOSE_SUBFOLDERS = ["git_subfolder"]
""" Folder to search for docker compose stacks"""

FOLDER_GIT_BASE = Path(__file__).parent.joinpath("git_base")
""" Fodler of the cloned git repo"""

FOLDER_RUNNING_STACK = Path(__file__).parent.joinpath("stack_running")
""" Fodler containing all files for currently running stack version"""

FOLDER_GOOD_STACK = Path(__file__).parent.joinpath("stack_good")
""" Fodler containing stack files for last known good stack version """


####################################################################################################
# Feature flags
####################################################################################################

FEATURE__MARK_BAD_STACK = False # ! not used yet
FEATURE__DEV__WRITE_COMMIT_HASH = True
FEATURE__DEV__DRY_RUN_CMDS = True # commands are not actually runn, and only print to console


##################################################
# Helth check
##################################################

STACK_HEALTHCHECK_TIMEOUT = 90

####################################################################################################
# GIT
####################################################################################################

GIT_URL = ""
GIT_USER = ""
GIT_PASS = ""
