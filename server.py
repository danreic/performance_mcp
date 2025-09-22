from fastmcp import FastMCP, Context
from typing import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pysrc import db_utils, jenkins, git_tools,sheets_utils
@dataclass
class AppResources:
    git_tools: git_tools.GitTools
    db: db_utils.PostgresDB
    jenkins: jenkins.Jenkins
    sheets: sheets_utils.GoogleSheetsClient


@asynccontextmanager
async def app_lifespan(mcp_Server: FastMCP) -> AsyncIterator[AppResources]:
    """
    Manages the lifecycle of the mcp server.
    """
    git_tools_instance = git_tools.GitTools()
    db_instance = db_utils.PostgresDB()
    db_instance.connect()
    jenkins_instance = jenkins.Jenkins()
    
    # Initialize GoogleSheetsClient with error handling
    try:
        sheets_instance = sheets_utils.GoogleSheetsClient()
        print("Google Sheets client initialized successfully")
    except Exception as e:
        print(f"Google Sheets client initialization failed: {e}")
        # Create a dummy object that will help with error reporting
        sheets_instance = f"Google Sheets initialization error: {str(e)}"
    
    yield AppResources(git_tools=git_tools_instance,db=db_instance, jenkins=jenkins_instance, sheets=sheets_instance)

    db_instance.close()

# Create a server instance with a descriptive name
mcp = FastMCP(name="Performace MCP", lifespan=app_lifespan)

@mcp.tool
async def get_uniq_from_url(run_url: str, ctx: Context) -> str:
    """
    Gets the uniq ID of a job from its jenkins URL

    Args:
        run_url: The URL of the jenkins job.

    Returns:
        The uniq ID of the job.
        with additional information from the jenkins job
    """
    jenkins_instance = ctx.request_context.lifespan_context.jenkins
    if not isinstance(run_url, str) or not run_url.strip():
        raise ValueError("Run URL must be a non-empty string.")

    try:
        response = jenkins_instance.get_job_uniq_id(run_url)[1]
        return response
    except Exception as e:
        return {"error": str(e)}

@mcp.tool
async def get_job_reults_from_url(run_url: str, ctx: Context) -> dict:
    """
    Gets the job results from a jenkins URL
    Args:
        run_url: The URL of the jenkins job.

    Returns:
        The job results from the jenkins job in a dictionary
    """
    jenkins_instance = ctx.request_context.lifespan_context.jenkins
    db_instance = ctx.request_context.lifespan_context.db
    try:
        rc, uniq_id = jenkins_instance.get_job_uniq_id(run_url)
    except Exception as e:
        return {"error": str(e)}
    if rc != 200:
        return {"error": "Failed to retrieve Uniq ID from Jenkins run URL."}
    else:
        raw_data = db_instance.fetch_test_data_by_uniq_id(uniq_id)
        if raw_data is None:
            return {"error": "No data found for Uniq ID."}
        else:
            return raw_data

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
def get_commits_diff(commit_hash1: str, commit_hash2: str = None, ctx: Context = None) -> str:
    """
    Gets the commits diff between two commit hashes or one commit hash
    can show maximum 50 commits diff at a time

    Args:
        commit_hash1: The first commit hash.
        commit_hash2: The second commit hash - Optional

    Returns:
        The commits diff between the two commit hashes.
        if it returnes empty it means no major diff between those two commits, only ones that arent src/ related
    """
    git_tools_instance = ctx.request_context.lifespan_context.git_tools
    diff = git_tools_instance.get_commits_diff(commit_hash1, commit_hash2)
    if diff == "":
        return "No major diff between those two commits, only ones that arent src/ related"
    else:
        return diff

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
def get_commit_diff_overview(commit_hash1: str, commit_hash2: str, ctx: Context = None) -> str:
    """
    Gets the commit diff overview between two commit hashes, gives you the commit, commit message, and the files that changed
    Args:
        commit_hash1: The first commit hash.
        commit_hash2: The second commit hash.

    Returns:
        The commit diff overview between the two commit hashes.
        List of commit hashes and the commit messages
    """
    git_tools_instance = ctx.request_context.lifespan_context.git_tools
    diff = git_tools_instance.get_commit_diff_overview(commit_hash1, commit_hash2)
    if diff == "":
        return "No major diff between those two commits, only ones that arent src/ related"
    else:
        return diff

@mcp.tool
def get_result_from_db(commit_hash1: str, commit_hash2: str = None, ctx: Context = None) -> str:
    """
    Gets the result from the database from all the commits between two commits or only one commit
    Args:
        commit_hash1: The first commit hash.
        commit_hash2: The  commit hash - Optional
        
    Returns:
        Database results of the requested commits

    """
    db_instance = ctx.request_context.lifespan_context.db
    git_tools_instance = ctx.request_context.lifespan_context.git_tools
    if commit_hash2 is not None:
        commits = git_tools_instance.get_commits_list(commit_hash1, commit_hash2)
    else:
        commits = [commit_hash1]
    results = db_instance.fetch_query("SELECT * FROM vperf WHERE commit_hash LIKE ANY (ARRAY %s)" % [f"%{commit_hash[:8]}%" for commit_hash in commits])
    return results


@mcp.tool
def trigger_job(job_name: str, params: dict, ctx: Context = None) -> str:
    """
    Triggers a job in jenkins
    Args:
        job_name: The name of the job to trigger.
        params: The parameters to pass to the job, example:
        {
            'pipeline': '1815451',
            'cluster_label': 'vast1206-kfs',
            'slash_filter': 'test_perf_block_agoda_8k_single_host_multiple_volumes_mixload',
            'install_flags': '--enable-encryption --enable-similarity --vsettings USE_FLASH_WB=false',
            'tests_file': 'other',
            'tests_path': 'pysrc/tests/performance/perf_block_tests.py',
            'rebuild_on_failure': 'true'
        }

    Returns:
        A message indicating if the job was triggered successfully or not
    """
    jenkins_instance = ctx.request_context.lifespan_context.jenkins
    try:
        response = jenkins_instance.trigger_job(job_name, params)
    except Exception as e:
        return f"Failed to trigger job: {str(e)}"
    if response.ok:
        return "Job triggered successfully"
    else:
        return f"Failed to trigger job: {response.status_code} {response.text}"

@mcp.tool
def get_jobs_from_cluster(cluster_label: str, ctx: Context = None) -> list:
    """
    Gets the latest jobs from jenkins that ran on a certain cluster
    Args:
        cluster_label: The label of the cluster.

    Returns:
        The jobs from jenkins that ran on the cluster.
        List of jobs with the job name and the build number
        Empty list if no jobs found
    """
    jenkins_instance = ctx.request_context.lifespan_context.jenkins
    jobs = jenkins_instance.get_jobs_from_cluster(cluster_label)
    if jobs:
        return jobs
    else:
        return []

@mcp.tool
def get_jobs_params(job_name: str, build_number: str, ctx: Context = None) -> dict:
    """
    Gets the parameters of a job from jenkins
    Args:
        job_name: The name of the job.
        build_number: The number of the build.

    Returns:
        The parameters of the job.
        Dictionary with the parameters
        error message if no parameters found
    """
    jenkins_instance = ctx.request_context.lifespan_context.jenkins
    params = jenkins_instance.get_jobs_params(job_name, build_number)
    if params:
        return params
    else:
        return {"error": "No parameters found for the job"}


@mcp.tool
def get_running_jobs(ctx: Context = None) -> dict:
    """
    Gets the running jobs from jenkins

    Returns:
        The running jobs from jenkins.
        List of jobs with the job name and the build number
        Empty list if no jobs found
    """
    jenkins_instance = ctx.request_context.lifespan_context.jenkins
    jobs = jenkins_instance.get_running_jobs()
    if jobs:
        return jobs
    else:
        return {"error": "No running jobs found"}

@mcp.tool
def abort_jenkins_job(job_name: str, build_number: str, ctx: Context = None) -> str:
    """
    Aborts a job in jenkins 
    Args:
        job_name: The name of the job to abort.
        build_number: The number of the build to abort.

    Returns:
        A message indicating if the job was aborted successfully or not
    """
    jenkins_instance = ctx.request_context.lifespan_context.jenkins
    response = jenkins_instance.abort_jenkins_job(job_name, build_number)
    if response.ok:
        return "Job aborted successfully"
    else:
        return f"Failed to abort job: {response.status_code} {response.text}"   

@mcp.tool
def extract_google_sheet_data(
        url_or_spreadsheet_id: str,
        range_name: str = "A:Z",
        sheet_name: str = None,
        ctx: Context = None
) -> dict:
    """
    Extract data from a Google Sheet with flexible range and sheet selection.
    Now supports both URLs and spreadsheet IDs.

    Args:
        url_or_spreadsheet_id: Complete Google Sheets URL or just the spreadsheet ID
        range_name: Cell range to extract (default: "A:Z")
        sheet_name: Name of specific sheet/tab (optional, ignored if URL contains gid)

    Returns:
        Dictionary containing extracted data with headers, rows, and metadata

    Examples:
        # Extract data using complete URL (recommended - includes specific sheet)
        extract_google_sheet_data("https://docs.google.com/spreadsheets/d/1S7-Uryb.../edit#gid=123456")

        # Extract data using spreadsheet ID (backward compatibility)
        extract_google_sheet_data("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")

        # Extract specific range using URL
        extract_google_sheet_data("https://docs.google.com/spreadsheets/d/1S7-Uryb.../edit#gid=123", "A1:E100")
    """

    sheets_instance = ctx.request_context.lifespan_context.sheets
    # Check if GoogleSheetsClient initialization failed
    if isinstance(sheets_instance, str):
        return {
            "success": False,
            "error": sheets_instance
        }

    try:
        # Check if input is a URL or spreadsheet ID
        if url_or_spreadsheet_id.startswith('https://docs.google.com/spreadsheets/'):
            # It's a URL - use the new URL-based method
            return sheets_instance.extract_sheet_data_from_url(url_or_spreadsheet_id, range_name)
        else:
            # It's a spreadsheet ID - use the old method for backward compatibility
            return sheets_instance.extract_sheet_data(url_or_spreadsheet_id, range_name, sheet_name)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@mcp.tool
def get_latest_sheet_from_spreadsheet(
        spreadsheet_id: str,
        ctx: Context = None
) -> dict:
    """
    Find the latest sheet by creation time in a Google Spreadsheet.
    
    Args:
        spreadsheet_id: The ID of the Google Spreadsheet
        
    Returns:
        Dictionary containing information about the latest sheet and metadata
        
    Examples:
        # Get latest sheet from spreadsheet ID
        get_latest_sheet_from_spreadsheet("1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms")
        
        # Get latest sheet from URL (extract ID first)
        get_latest_sheet_from_spreadsheet("1S7-Uryb...")
    """
    
    sheets_instance = ctx.request_context.lifespan_context.sheets
    # Check if GoogleSheetsClient initialization failed
    if isinstance(sheets_instance, str):
        return {
            "success": False,
            "error": sheets_instance
        }

    try:
        return sheets_instance.get_latest_sheet_by_creation_time(spreadsheet_id)
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

if __name__ == "__main__":
    mcp.run()