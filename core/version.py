"""
Version tracking for Herald bot.
Captures git commit hash to uniquely identify each deployment.
Works with Railway environment variables and local git commands.
"""
import subprocess
import uuid
import os
from datetime import datetime

# Generate a unique instance ID each time the bot starts
INSTANCE_ID = str(uuid.uuid4())[:8]

def get_git_commit() -> str:
    """Get the current git commit hash from Railway env or git command."""
    # Try Railway environment variable first (production)
    railway_commit = os.getenv('RAILWAY_GIT_COMMIT_SHA')
    if railway_commit:
        # Railway provides full SHA, truncate to 7 chars like git --short
        return railway_commit[:7]

    # Fall back to git command (local development)
    try:
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return commit
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"

def get_git_branch() -> str:
    """Get the current git branch name from Railway env or git command."""
    # Try Railway environment variable first (production)
    railway_branch = os.getenv('RAILWAY_GIT_BRANCH')
    if railway_branch:
        return railway_branch

    # Fall back to git command (local development)
    try:
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        return branch
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"

# Bot version information
BOT_VERSION = "1.0.0"  # Semantic version
GIT_COMMIT = get_git_commit()
GIT_BRANCH = get_git_branch()
STARTUP_TIME = datetime.utcnow()

def get_version_string() -> str:
    """Get a formatted version string for display."""
    return f"v{BOT_VERSION} ({GIT_COMMIT})"

def get_full_version_info() -> dict:
    """Get complete version information as a dictionary."""
    return {
        "version": BOT_VERSION,
        "commit": GIT_COMMIT,
        "branch": GIT_BRANCH,
        "instance_id": INSTANCE_ID,
        "startup_time": STARTUP_TIME
    }
