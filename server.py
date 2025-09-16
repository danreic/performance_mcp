from fastmcp import FastMCP
from pysrc.jenkins import get_run_uniq

# Create a server instance with a descriptive name
mcp = FastMCP(name="My AI Agent Server")

@mcp.tool
def get_uniq_from_url(run_url: str) -> dict:
    """
    Gets the uniq ID of a job from its jenkins URL

    Args:
        run_url: The URL of the jenkins job.

    Returns:
        The uniq ID of the job.
    """
    if not isinstance(run_url, str) or not run_url.strip():
        raise ValueError("Run URL must be a non-empty string.")

    try:
        response = get_run_uniq(run_url)[0]
        return response
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()