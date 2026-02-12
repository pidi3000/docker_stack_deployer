
import config

import logging

from pathlib import Path
from urllib.parse import urlparse, urlunparse, ParseResult
from git import Repo, GitCommandError, InvalidGitRepositoryError


####################################################################################################

logger = logging.getLogger(config.FEATURE__LOGGING__BASE_NAME).getChild(__name__)

# logger = logging.getLogger(__name__)

####################################################################################################


def _append_file_change(changed_files: list[Path], file_path, change_string) -> list[Path]:
    def _in_watched_folder(p: Path) -> bool:
        for sub_folder in config.COMPOSE_SUBFOLDERS:
            # logger.debug(sub_folder, "  \t", p)
            if p.is_relative_to(sub_folder):
                return True

        return False

    ########################################
    file_path = Path(file_path)
    if _in_watched_folder(file_path):
        changed_files.append((file_path, change_string))

    return changed_files

####################################################################################################

def _load_last_commit_hash(state_file:Path):
    if state_file.exists():
        with state_file.open('r') as f:
            previous_commit = f.read().strip()
        return previous_commit
    
    return None

def _write_last_commit_hash(state_file:Path, commit_hahs:str):
    if config.FEATURE__DEV__WRITE_COMMIT_HASH:
        with state_file.open('w') as f:
            f.write(commit_hahs)

def _clone_repo(repo_url, repo_dir: Path, state_file: Path):

    changed_files = []

    # Clone the repository if it doesn't exist
    if hasattr(config, "GIT_BRANCH") and len(config.GIT_BRANCH.strip()) > 1:
        Repo.clone_from(repo_url, repo_dir, branch=config.GIT_BRANCH)
    else:
        Repo.clone_from(repo_url, repo_dir)

    # Save the initial commit hash
    repo = Repo(repo_dir)
    _write_last_commit_hash(state_file, repo.head.commit.hexsha)
    # with state_file.open('w') as f:
    #     f.write(repo.head.commit.hexsha)

    # On the first clone, list all files as 'added'
    for file_path in repo.head.commit.tree.traverse():
        # Only include files (not directories)
        if file_path.type == 'blob':
            changed_files = _append_file_change(
                changed_files, file_path.path, "added")
            # changed_files.append((file_path.path, 'added'))

    return f"Cloned repository from '{config.GIT_URL}' into '{repo_dir}'", changed_files


def _pull_repo(repo_dir: Path, state_file: Path):
    changed_files = []

    repo = Repo(repo_dir)
    if not repo.bare:
        previous_commit = _load_last_commit_hash(state_file)

        # Pull the latest changes
        origin = repo.remotes.origin
        origin.pull()

        # Get the latest commit after pull
        latest_commit = repo.head.commit

        if previous_commit:
            # Compare with the last known commit
            for diff in latest_commit.diff(previous_commit):
                # changed_files.append((diff.a_path, diff.change_type))

                if diff.change_type == 'A':
                    # changed_files.append((diff.a_path, 'added'))
                    changed_files = _append_file_change(
                        changed_files, diff.a_path, "added")
                elif diff.change_type == 'M':
                    # changed_files.append((diff.a_path, 'modified'))
                    changed_files = _append_file_change(
                        changed_files, diff.a_path, "modified")
                elif diff.change_type == 'D':
                    # changed_files.append((diff.a_path, 'deleted'))
                    changed_files = _append_file_change(
                        changed_files, diff.a_path, "deleted")
        else:
            # If no previous commit exists, list all files as 'added'
            for file_path in repo.head.commit.tree.traverse():
                # Only include files (not directories)
                if file_path.type == 'blob':
                    # changed_files.append((file_path.path, 'added'))
                    changed_files = _append_file_change(
                        changed_files, file_path.path, "added")

        # Save the latest commit hash for future comparisons

        _write_last_commit_hash(state_file, repo.head.commit.hexsha)
        # if config.FEATURE__DEV__WRITE_COMMIT_HASH:
        #     with state_file.open('w') as f:
        #         f.write(latest_commit.hexsha)

        return f"Updated the existing repository in '{repo_dir}'", changed_files
    else:
        return f"The repository in '{repo_dir}' is bare.", changed_files


def _clone_or_update_repo(repo_url, repo_dir, state_file="git_last_commit.txt"):
    """
    Clones a Git repository if it doesn't exist locally. 
    If it exists, pulls the latest changes and returns a list of changed files since the last update.
    If no previous commit is found, lists all files in the repo as added.

    Args:
    repo_url (str): The URL of the git repository to clone or update.
    repo_dir (str): The local directory to clone into or pull from.
    state_file (str): Path to the file that stores the last checked commit hash.

    Returns:
    tuple: A message indicating whether the repository was cloned or updated,
           and a list of changed files with their statuses (added, modified, deleted).
    """
    repo_dir = Path(repo_dir)  # Convert the directory to a Path object
    state_file = Path(state_file)
    # state_file = Path(str(repo_dir) + "-" + state_file)
    # state_file = repo_dir.joinpath(state_file)

    # logger.debug(state_file)
    logger.debug(f"Last commit hash saved in '{state_file}': {_load_last_commit_hash(state_file)}")

    
    
    
    message = None
    changed_files = []

    try:
        changed_files = []
        previous_commit = None

        # If the directory already contains a git repo, pull updates
        if repo_dir.exists() and repo_dir.is_dir():
            message, changed_files = _pull_repo(repo_dir, state_file)

        else:
            message, changed_files = _clone_repo(
                repo_url, repo_dir, state_file)

    except (GitCommandError, InvalidGitRepositoryError) as e:
        raise
        return f"An error occurred while handling the repository: {e}", []

    return message, changed_files


####################################################################################################
####################################################################################################

def _add_credentials_to_url(url, username, password):
    # Parse the given URL into components
    # logger.debug(url)
    # logger.debug(username)
    # logger.debug(password)
    parsed_url: ParseResult = urlparse(url)

    # Construct netloc with username and password
    new_netloc = f"{username}:{password}@{parsed_url.netloc}"

    # Rebuild the URL with the new credentials
    new_url = parsed_url._replace(netloc=new_netloc)

    # Return the reconstructed URL
    return urlunparse(new_url)


def load_git_repo() -> list[Path, str]:
    repo_url = _add_credentials_to_url(
        url=config.GIT_URL,
        username=config.GIT_USER,
        password=config.GIT_PASS
    )
    
    repo_url_censored = _add_credentials_to_url(
        url=config.GIT_URL,
        username=config.GIT_USER,
        password=f"{config.GIT_PASS[:20]}{'*'*40}"
    )

    # repo_dir = Path(__file__).parent.joinpath(config.GIT_BASE_FOLDER)
    repo_dir = config.FOLDER_GIT_BASE

    logger.debug(f"repo_url={repo_url_censored}")
    logger.debug(f"repo_dir={str(repo_dir)}")

    message, changes = _clone_or_update_repo(repo_url, repo_dir)
    changes = [(config.FOLDER_GIT_BASE.joinpath(change[0]), change[1])
               for change in changes]

    logger.debug(message)

    if changes:
        # logger.debug("Changed files:")
        _change_str = "Git file changes:\n"

        for file, status in changes:
            _change_str = _change_str + f"{' '*4}{str(file.relative_to(config.FOLDER_GIT_BASE)):<15}: {status}\n"

        logger.debug(_change_str)

    else:
        logger.debug("No changes detected.")

    return changes
