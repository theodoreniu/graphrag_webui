import io
import time
import streamlit as st
import os
from dotenv import load_dotenv
from libs.common import format_project_name, get_project_names, run_command
import libs.config as config
from contextlib import redirect_stdout
import asyncio
from graphrag.cli.initialize import initialize_project_at
import yaml
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

load_dotenv()


def initialize_project(path):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    output = io.StringIO()

    try:
        with redirect_stdout(output):
            initialize_project_at(path=path, force=False)
        output_value = output.getvalue()
        st.success(output_value)
    finally:
        loop.close()


def overwrite_settings_yaml(root, new_project_name, create_db_type):
    settings_yaml = f"{root}/settings.yaml"

    run_command(f"cp {root}/settings.yaml {root}/settings_default.yaml")

    template_settings_yaml = f"/app/template/setting_{create_db_type}.yaml"

    container_name = f"{config.app_name}_{new_project_name}"
    with open(template_settings_yaml, "r") as t:
        with open(settings_yaml, "w") as f:
            new_settings_yaml = t.read().replace(
                "container_name: default", f"container_name: {container_name}"
            ).replace(
                'base_dir: "logs"', f'base_dir: "{root}/logs"'
            ).replace(
                'base_dir: "output"', f'base_dir: "{root}/output"'
            ).replace(
                "db_uri: 'lancedb'", f"db_uri: '{root}/lancedb'"
            )
            f.write(new_settings_yaml)


def overwrite_settings_env(root):
    settings_env = f"{root}/.env"
    template_settings_env = f"/app/template/.env"
    with open(template_settings_env, "r") as t:
        with open(settings_env, "w") as f:
            f.write(t.read())


def create_project():
    project_name_list = get_project_names()
    new_project_value = "Just New Project"
    st.markdown("----------------------------")
    st.markdown("## New Project")
    today_hour = time.strftime("%Y%m%d%H", time.localtime())
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        new_project_name = st.text_input(
            "Please input name",
            value=today_hour,
            max_chars=30,
        )
    with c2:
        project_name_list.insert(0, new_project_value)
        copy_from_project_name = st.selectbox(
            "Copy from", project_name_list, key="create_from_project_name"
        )
    with c3:
        create_for_username = "admin"
        usernames = ["Anonymous"]
        if os.path.exists("./config.yaml"):
            with open("./config.yaml") as file:
                yaml_config = yaml.load(file, Loader=SafeLoader)
                usernames = yaml_config["credentials"]["usernames"].keys()
        create_for_username = st.selectbox(
            "Create for", usernames, key="create_for_user_name"
        )
    with c4:
        create_db_type = st.selectbox(
            "Vector DB", ['lancedb', 'ai_search'], key="create_db_type"
        )

    btn = st.button("Create", key="confirm", icon="🚀")
    if btn:
        formatted_project_name = format_project_name(
            f"{create_for_username}_{new_project_name}")

        if check_project_exists(formatted_project_name):
            st.error(f"Project {formatted_project_name} already exists.")
            return

        root = os.path.join("/app", "projects", formatted_project_name)

        try:
            if copy_from_project_name == new_project_value:
                initialize_project(path=root)
                # overwrite_settings_yaml(
                #     root, formatted_project_name, create_db_type)
                # overwrite_settings_env(root)
            else:
                copy_project(copy_from_project_name, formatted_project_name)
        except Exception as e:
            st.error(str(e))


def modify_project_prompt(
    formatted_project_name, file_name, search_text, project_language, type
):
    prompt_file = f"/app/projects/{formatted_project_name}/prompts/{file_name}"
    if os.path.exists(prompt_file):
        with open(prompt_file, "r") as f:
            prompt_content = f.read()
            new_prompt_content = prompt_content.replace(
                search_text,
                f"{search_text} You should use {project_language} for {type} description.",
            )
            with open(prompt_file, "w") as f:
                f.write(new_prompt_content)


def check_project_exists(formatted_project_name: str):
    return os.path.exists(f"/app/projects/{formatted_project_name}")


def copy_project(copy_from_project_name: str, formatted_project_name: str):
    run_command(
        f"cp -r '/app/projects/{copy_from_project_name}' '/app/projects/{formatted_project_name}'"
    )
    st.success(
        f"Project {copy_from_project_name} copied to {formatted_project_name}")
    time.sleep(3)
