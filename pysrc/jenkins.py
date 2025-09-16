import requests
import re
import os

JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
USERNAME = os.getenv("JENKINS_USERNAME")

def extract_test_suite_from_path(path):
    try:
        file_name = path.split("/")[-1]
        if "." in file_name:
            file_name = file_name.split(".")[0]
            return file_name
    except Exception as e:
        print(f"Error extracting test suite from path '{path}': {e}")
        return "UnknownTestSuite"


def get_test_finish_status(jenkins_run_url):
    """
    Fetches the test finish status from a Jenkins job URL.
    """

    auth = (USERNAME, JENKINS_API_TOKEN)
    url = parse_jenkins_url(jenkins_run_url)
    response = requests.get(url, auth=auth)

    # Split into lines and take last 10
    lines = response.text.strip().split("\n")[-10:]
    last_part = "\n".join(lines)


    status_match = re.search(r"Finished:\s*(\w+)", last_part)
    status = status_match.group(1) if status_match else None

    return status


def extract_protocol_and_test_suit_from_url(url):
    """
    Extracts the job name from a Jenkins job URL.
    """

    url = parse_jenkins_url(url, json=True)
    resp = requests.get(url, auth=(USERNAME, JENKINS_API_TOKEN))
    resp.raise_for_status()
    data = resp.json()

    # Example: Get parameters
    parameters = {}
    for action in data.get("actions", []):
        if "parameters" in action:
            for param in action["parameters"]:
                parameters[param["name"]] = param["value"]

    # Extract relevant parameters
    protocol = parameters.get("INFRA_PROTOCOL", "None")
    cluster =parameters.get("cluster_label", "None")
    test_suite = parameters.get("tests_file", "None")
    if test_suite == "other":
        test_suite = parameters.get("tests_list", "None")

    if test_suite and test_suite != "other":
        test_suite = extract_test_suite_from_path(test_suite)
    return protocol, test_suite, cluster


def parse_jenkins_url(url,json=False):
    """
    Extracts Jenkins base URL, job name, and build number from a Jenkins job URL.
    """
    # Match pattern
    pattern = re.compile(r"(https?://[^/]+)/job/([^/]+)/(\d+)")
    match = pattern.match(url)

    if not match:
        raise ValueError("Invalid Jenkins URL format")

    jenkins_url, job_name, build_number = match.groups()

    # print(f"Jenkins URL: {jenkins_url}, Job Name: {job_name}, Build Number: {build_number}")

    def url_join(*parts):
        return "/".join(part.strip("/") for part in parts)

    if json:
        return url_join(jenkins_url, "job", job_name, str(build_number), "api", "json")

    return url_join(jenkins_url, "job", job_name, str(build_number), "consoleText")


def get_job_uniq_id(jenkins_run_url):
    auth = (USERNAME, JENKINS_API_TOKEN)
    url = parse_jenkins_url(jenkins_run_url)
    response = requests.get(url, auth=auth)
    uniq_id = None

    def extract_uniq(console_log):
        ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
        clean_log = ansi_escape.sub('', console_log)
        match = re.search(r"^\s*Uniq\s+(\d{10})\s*$", clean_log, re.MULTILINE)
        if match:
            return match.group(1)
        return None

    if response.status_code == 200:
        console_log = response.text
        uniq_id = extract_uniq(console_log)
        if uniq_id:
            print(f"Extracted Uniq ID: {uniq_id}")
        else:
            print("No Uniq ID found in the console log.")
    return response.status_code, uniq_id


def fetch_test_data_by_uniq_id(uniq_id):
    """
    Fetches test data from the database using the Uniq ID.
    """

    job_data = DB.fetch_query("select date,build,test_name,bw,iops,latency,cluster,uniq from vperf where uniq=%s;", (uniq_id,))
    if job_data:
        # print(f"Job Data: had been fetched for Uniq ID: {uniq_id}")
        return job_data
    else:
        print(f"No data found for Uniq ID: {uniq_id}")
        return None


def get_job_data(jenkins_run_url):
    """
    Main function to get job data from Jenkins and database.
    """
    rc, uniq_id = get_job_uniq_id(jenkins_run_url)
    if uniq_id:
        raw_data = fetch_test_data_by_uniq_id(uniq_id)
        return raw_data
    else:
        print("Failed to retrieve Uniq ID from Jenkins run URL.")
        return None


def get_result_dict(rows):
    data = dict()
    date, build, cluster, uniq = (None, None, None, None)
    for row in rows:
        date, build, test_name, bw, iops, latency, cluster, uniq = row
        if "4K" in test_name:
            data[test_name] = iops
        else:
            data[test_name] = bw
    data.update(date=date.strftime("%B %d, %Y"), build=build, cluster=cluster, uniq=uniq)
    return data


def get_data(run_url):

    rows = get_job_data(run_url)
    if not rows:
        print(f"No data found for run: {run_url}")
        return None
    else:
        data = get_result_dict(rows)
        ordered_data, ordered_keys = order_data_by_test_name(data)
        return ordered_data, ordered_keys


def order_data_by_test_name(data):
    """
    Orders the performance data by test name.
    """
    keys = list(data.keys())
    ordered_data = []
    for key in ["date", "build", "cluster", "uniq"]:
        if key in keys:
            ordered_data.append(data.get(key, "-"))
            keys.remove(key)

    keys.sort()
    for key in keys:
        ordered_data.append(data.get(key, "-"))
    ordered_keys = ["date", "build", "cluster", "uniq"] + keys
    return ordered_data, ordered_keys



def validate_run_url(url):
    if not isinstance(url, str):
        return None, "Run URL must be a string."
    return url, "Run URL is valid."


def get_run_uniq(run_url):
    url, stat = validate_run_url(run_url)
    if not url:
        return dict(message=f"❌ Invalid run URL: {stat}"), 400

    try:
        print(f"Fetching Unique ID for run URL: {run_url}")
        protocol, test_suite, cluster = extract_protocol_and_test_suit_from_url(run_url)
        status_code, uniq_id = get_job_uniq_id(run_url)
        if status_code == 200:
            return dict(message=f"✅ Unique ID for the run : {uniq_id}", uniq_id=uniq_id, protocol=protocol, test_suite=test_suite, cluster=cluster), status_code
        else:
            return dict(message=f"❌ Failed to retrieve Unique ID. HTTP Status Code: {status_code}", uniq_id=uniq_id), status_code
    except Exception as e:
        return dict(message=f"❌ Error retrieving Unique ID: {str(e)}"), 500




