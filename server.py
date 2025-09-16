from fastmcp import FastMCP, Context
from pysrc.jenkins import get_run_uniq
from pysrc import git_tools
from typing import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pysrc import db_utils
@dataclass
class AppResources:
    git_tools: git_tools.GitTools
    db: db_utils.PostgresDB


@asynccontextmanager
async def app_lifespan(mcp_Server: FastMCP) -> AsyncIterator[AppResources]:
    """
    Manages the lifecycle of the mcp server.
    """
    git_tools_instance = git_tools.GitTools()
    db_instance = db_utils.PostgresDB()
    
    yield AppResources(git_tools=git_tools_instance, db=db_instance)

    db_instance.close()

# Create a server instance with a descriptive name
mcp = FastMCP(name="Performace MCP", lifespan=app_lifespan)

@mcp.tool
async def get_uniq_from_url(run_url: str) -> dict:
    """
    Gets the uniq ID of a job from its jenkins URL

    Args:
        run_url: The URL of the jenkins job.

    Returns:
        The uniq ID of the job.
        with additional information from the jenkins job
    """
    if not isinstance(run_url, str) or not run_url.strip():
        raise ValueError("Run URL must be a non-empty string.")

    try:
        response = get_run_uniq(run_url)[0]
        return response
    except Exception as e:
        return {"error": str(e)}

@mcp.tool
async def get_commit_hash_from_pipeline_id(pipeline_id: int, ctx: Context) -> str:
    """
    Gets the commit hash of a pipeline from its pipeline ID

    Args:
        pipeline_id: The ID of the pipeline.

    Returns:
        The commit hash of the pipeline.
    """
    git_tools_instance = ctx.request_context.lifespan_context.git_tools
    return git_tools_instance.get_hash_from_pipeline_id(pipeline_id)

@mcp.tool
def get_commits_diff(commit_hash1: str, commit_hash2: str, ctx: Context) -> str:
    """
    Gets the commits diff between two commit hashes

    Args:
        commit_hash1: The first commit hash.
        commit_hash2: The second commit hash.

    Returns:
        The commits diff between the two commit hashes.
    """
    git_tools_instance = ctx.request_context.lifespan_context.git_tools
    return git_tools_instance.get_commits_diff(commit_hash1, commit_hash2)

@mcp.tool
def get_commits_list(commit_hash1: str, commit_hash2: str, ctx: Context = None) -> list:
    """
    Gets the git commits list between two commit hashes (git ll with only first parent commits) between two commit hashes
    Gets Only the commit hashes

    Args:
        commit_hash1: The first commit hash.
        commit_hash2: The second commit hash.

    Returns:
        The git commits list between the two commit hashes.
    """
    git_tools_instance = ctx.request_context.lifespan_context.git_tools
    return git_tools_instance.get_commits_list(commit_hash1, commit_hash2)

@mcp.tool
def get_git_llfp(commit_hash1: str, commit_hash2: str = None, ctx: Context = None) -> list:
    """
    Gets the git llfp (git ll with only first parent commits) between two commit hashes
    Gets the commit hashes and the commit messages
    Args:
        commit_hash1: The first commit hash.
        commit_hash2: The second commit hash - Optional

    Returns:
        The git llfp between the two commit hashes or the git llfp of the commit hash if commit_hash2 is not provided.
        List of commit hashes and the commit messages
    """
    git_tools_instance = ctx.request_context.lifespan_context.git_tools
    return git_tools_instance.get_git_llfp(commit_hash1, commit_hash2).split("\n")


if __name__ == "__main__":
    mcp.run()