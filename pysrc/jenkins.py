import requests
import re
import os




class Jenkins:
    def __init__(self):
        self.JENKINS_API_TOKEN = os.getenv("JENKINS_API_TOKEN")
        self.USERNAME = os.getenv("JENKINS_USERNAME")
        self.JENKINS_URL = os.getenv("JENKINS_URL")
        self.JENKINS_PORT = os.getenv("JENKINS_PORT", "8080")
    
    def get_request(self, url, **params):
        response = requests.get(url, auth=(self.USERNAME, self.JENKINS_API_TOKEN), data=params)
        response.raise_for_status()
        return response

    def post_request(self, url, params):
        response = requests.post(url, auth=(self.USERNAME, self.JENKINS_API_TOKEN), data=params)
        response.raise_for_status()
        return response

    def get_test_finish_status(self, jenkins_run_url):
        """
        Fetches the test finish status from a Jenkins job URL.
        """

        url = parse_jenkins_url_for_build(jenkins_run_url)
        response = self.get_request(url)

        # Split into lines and take last 10
        lines = response.text.strip().split("\n")[-10:]
        last_part = "\n".join(lines)


        status_match = re.search(r"Finished:\s*(\w+)", last_part)
        status = status_match.group(1) if status_match else None

        return status

    def extract_protocol_and_test_suit_from_url(self, url):
        """
        Extracts the job name from a Jenkins job URL.
        """

        url = parse_jenkins_url_for_build(url, json=True)
        response = self.get_request(url)
        data = response.json()

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

    def get_job_uniq_id(self, jenkins_run_url):
        url = parse_jenkins_url_for_build(jenkins_run_url)
        response = self.get_request(url)
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

    def trigger_job(self, job_name="run_tests_vperfv2", params=None):
        url = f"{self.JENKINS_URL}:{self.JENKINS_PORT}/job/{job_name}/buildWithParameters"
        response = self.post_request(url, params)
        return response


def extract_test_suite_from_path(path):
    try:
        file_name = path.split("/")[-1]
        if "." in file_name:
            file_name = file_name.split(".")[0]
            return file_name
    except Exception as e:
        print(f"Error extracting test suite from path '{path}': {e}")
        return "UnknownTestSuite"



def parse_jenkins_url_for_build(url,json=False):
    """
    Extracts Jenkins base URL, job name, and build number from a Jenkins job URL.
    """
    # Match pattern
    pattern = re.compile(r"(https?://[^/]+)/job/([^/]+)/(\d+)")
    match = pattern.match(url)

    if not match:
        raise ValueError("Invalid Jenkins URL format")

    jenkins_url, job_name, build_number = match.groups()


    def url_join(*parts):
        return "/".join(part.strip("/") for part in parts)

    if json:
        return url_join(jenkins_url, "job", job_name, str(build_number), "api", "json")

    return url_join(jenkins_url, "job", job_name, str(build_number), "consoleText")


def validate_run_url(url):
    if not isinstance(url, str):
        return None, "Run URL must be a string."
    return url, "Run URL is valid."

