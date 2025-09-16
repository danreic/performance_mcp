import git
import os
import requests


class GitTools:
    def __init__(self):
        self.local_repo_path = os.getenv("LOCAL_REPO_PATH")
        self.gitlab_url = os.getenv("GITLAB_URL")
        self.base_gitlab_url = self.gitlab_url.split(".com")[0] + ".com"
        self.gitlab_token = os.getenv("GITLAB_TOKEN")

        if os.path.exists(self.local_repo_path):
            print(f"Repository already exists at '{self.local_repo_path}'")
            self.repo = git.Repo(self.local_repo_path)
        else:
            print(f"Cloning repository from {self.gitlab_url}...")
            self.repo = git.Repo.clone_from(self.gitlab_url, self.local_repo_path)

    def get_repo(self):
        return self.repo
    
    def get_commits_diff(self, commit_sha1, commit_sha2):
        return self.repo.git.diff(commit_sha1, commit_sha2)
    
    def get_shortlog(self, commit_sha1, commit_sha2):
        return self.repo.git.shortlog(commit_sha1, commit_sha2)

    def get_hash_from_pipeline_id(self, pipeline_id):
        url = f"{self.base_gitlab_url}/api/v4/projects/3/pipelines/{pipeline_id}"
        response = requests.get(url, headers={"PRIVATE-TOKEN": self.gitlab_token})
        return response.json()["sha"]

    def get_git_llfp(self, commit_sha1, commit_sha2=None):
        if commit_sha2 is None:
            return self.repo.git.log("--first-parent", "--pretty=format:%H", commit_sha1)
        return self.repo.git.log("--first-parent", "--pretty=format:%H", f"{commit_sha1}..{commit_sha2}")

    def get_git_llfp_more_data(self, commit_sha1, commit_sha2=None):
        if commit_sha2 is None:
            return self.repo.git.llfp(commit_sha1)
        return self.repo.git.llfp(f"{commit_sha1}..{commit_sha2}")
