import json
import re
import os
import subprocess
import streamlit as st
from theodoretools.fs import list_subdirectories
import libs.config as config
from graphrag.config.load_config import load_config
from pathlib import Path
import hashlib
from dotenv import load_dotenv


def load_project_env(project_name: str):
    load_dotenv(dotenv_path=f"/app/projects/{project_name}/.env", override=True)


def project_path(project_name: str):
    return Path("/app/projects") / project_name


def load_graphrag_config(project_name: str):
    return load_config(root_dir=project_path(project_name))


def set_venvs(project_name: str):
    os.environ["GRAPHRAG_ENTITY_EXTRACTION_PROMPT_FILE"] = str(
        Path("/app/projects") / project_name / "prompts" / "entity_extraction.txt"
    )
    os.environ["GRAPHRAG_COMMUNITY_REPORT_PROMPT_FILE"] = (
        f"/app/projects/{project_name}/prompts/community_report.txt"
    )
    os.environ["GRAPHRAG_SUMMARIZE_DESCRIPTIONS_PROMPT_FILE"] = (
        f"/app/projects/{project_name}/prompts/summarize_descriptions.txt"
    )


def is_built(project_name: str):
    project_base = f"/app/projects/{project_name}/output"

    if not os.path.exists(project_base):
        return False

    files = os.listdir(project_base)

    if len(files) == 0:
        return False

    elements_set = [
        "communities.parquet",
        "entities.parquet",
        "text_units.parquet",
        "community_reports.parquet",
        # "final_nodes.parquet",
        "stats.json",
        "documents.parquet",
        "relationships.parquet",
    ]

    return set(elements_set).issubset(set(files))


def check_rag_complete(project_name: str):
    base_path = f"/app/projects/{project_name}"
    subdirectories = list_subdirectories(path=f"{base_path}/output")
    if len(subdirectories) == 0:
        raise Exception("Your need to build index first.")


def get_original_dir(project_name: str):
    return f"/app/projects/{project_name}/original"


def list_files_and_sizes(directory: str):
    file_list = []
    for root, dirs, files in os.walk(f"{directory}/"):
        for file in files:
            file_path = os.path.join(root, file)
            file_size_bytes = os.path.getsize(file_path)
            if file_size_bytes == 0:
                file_list.append((file, file_path, f"0"))
            elif file_size_bytes < 1024:
                file_list.append((file, file_path, f"({file_size_bytes:.5f}B)"))
            elif file_size_bytes < 1024 * 1024:
                file_size_kb = file_size_bytes / 1024
                file_list.append((file, file_path, f"({file_size_kb:.5f}KB)"))
            else:
                file_size_mb = file_size_bytes / (1024 * 1024)
                file_list.append((file, file_path, f"({file_size_mb:.5f}MB)"))

    return file_list


def is_admin():
    if not os.path.exists("./config.yaml"):
        return True

    if (
        "authentication_status" in st.session_state
        and st.session_state["authentication_status"]
    ):
        return st.session_state["username"].lower() == "admin"

    return True


def is_project_admin(project_name: str):
    if not os.path.exists("./config.yaml"):
        return True

    if is_admin():
        return True

    if (
        "authentication_status" in st.session_state
        and st.session_state["authentication_status"]
    ):
        usernmae = st.session_state["username"].lower()
        return usernmae.endswith("_admin") and project_name.startswith(
            usernmae.replace("_admin", "")
        )

    return True


def can_test_project(project_name: str):
    if not os.path.exists("./config.yaml"):
        return True

    if is_project_admin(project_name):
        return True

    if (
        "authentication_status" in st.session_state
        and st.session_state["authentication_status"]
    ):
        return project_name.startswith(get_project_prefix_by_username())

    return True


def get_project_prefix_by_username():
    if not os.path.exists("./config.yaml"):
        return ""

    if (
        "authentication_status" in st.session_state
        and st.session_state["authentication_status"]
    ):
        usernmae = st.session_state["username"].lower()
        return usernmae.replace("_admin", "")

    return True


def get_username():
    if st.session_state["authentication_status"]:
        return st.session_state["username"]
    return config.app_name


def format_project_name(version: str):
    if not re.match("^[A-Za-z0-9_-]*$", version):
        raise ValueError("Name can only contain letters and numbers.")

    if is_admin():
        return version.lower()

    return f"{get_username()}_{version.lower()}"


def delete_project_name(project_name: str):
    run_command(f"rm -rf /app/projects/{project_name}")
    st.success(f"Deleted {project_name}")


def project_name_exists(project_name: str):
    project_path = f"/app/projects/{project_name}"
    return os.path.exists(project_path)


def get_project_names():
    project_name_path = "/app/projects"
    projects = list_subdirectories(project_name_path)

    if is_admin():
        return projects

    list = []
    for p in projects:
        if can_test_project(p):
            list.append(p)
    return list


def run_command(command: str, output: bool=False):
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    while True:
        stdout = process.stdout.readline()
        stderr = process.stderr.readline()

        if output and stderr:
            st.error(stderr)

        if stdout == "" and process.poll() is not None:
            break
        if stdout:
            s = stdout.strip()
            if output:
                st.write(s)
            elif s.startswith("🚀"):
                st.write(s)

    rc = process.poll()
    return rc


def generate_text_fingerprint(text, algorithm="sha256"):
    hash_object = hashlib.new(algorithm)
    hash_object.update(text.encode("utf-8"))
    return hash_object.hexdigest()


def get_cache_json_from_file(cache_key: str):
    cache_file = f"/app/cache/query_cache/{cache_key}.json"
    if os.path.exists(cache_file):
        with open(cache_file, "r") as file:
            return json.load(file)
    return None


def set_cache_json_to_file(cache_key: str, data: dict):
    cache_file = f"/app/cache/query_cache/{cache_key}.json"
    cache_file_dir = os.path.dirname(cache_file)
    if not os.path.exists(cache_file_dir):
        os.makedirs(cache_file_dir, exist_ok=True)

    with open(cache_file, "w") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
