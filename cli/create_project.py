from cli.common import run_command
import os
from cli.logger import get_logger
import libs.config as config
import time
from pathlib import Path
from graphrag.cli.initialize import initialize_project_at

logger = get_logger('create_project_cli')

root_project_dir = os.path.dirname(os.path.dirname(__file__))


def overwrite_settings_yaml(project_dir, new_project_name, create_db_type="ai_search"):
    settings_yaml = f"{project_dir}/settings.yaml"

    run_command(f"cp {project_dir}/settings.yaml {project_dir}/settings_default.yaml")

    template_settings_yaml = f"{root_project_dir}/template/setting_{create_db_type}_cli.yaml"

    container_name = f"{config.app_name}_{new_project_name}"
    
    with open(template_settings_yaml, "r") as t:
        with open(settings_yaml, "w") as f:
            new_settings_yaml = t.read().replace(
                "container_name: default", f"container_name: {container_name}"
            ).replace(
                'base_dir: "cache"', f'base_dir: "/app/{project_dir}/cache"'
            ).replace(
                'base_dir: "logs"', f'base_dir: "/app/{project_dir}/logs"'
            ).replace(
                'base_dir: "output"', f'base_dir: "/app/{project_dir}/output"'
            ).replace(
                "db_uri: 'lancedb'", f"db_uri: '/app/{project_dir}/lancedb'"
            )
            f.write(new_settings_yaml)
    

def overwrite_settings_env(root_dir):
    settings_env = f"{root_dir}/.env"
    template_settings_env = f"{root_project_dir}/template/.env"
    with open(template_settings_env, "r") as t:
        with open(settings_env, "w") as f:
            f.write(t.read())


def init_graphrag_project(project_name: str):
    """ initialize graphrag project
    
    Args:
        project_name: project name, if empty, use default name
        
    Returns:
        bool: if initialize successfully
    """
    logger.info("initialize graphrag project")

    if not project_name:
        project_name = f"cli_{time.strftime('%Y%m%d')}"

    # create projects directory
    projects_dir = Path('projects')
    if not projects_dir.exists():
        logger.info("create projects directory")
        projects_dir.mkdir()

    # check if project directory exists
    project_dir = os.path.join(projects_dir, project_name)
    if os.path.exists(project_dir):
        logger.error(f"project {project_name} already exists")
        return False

    initialize_project_at(
        path=project_dir,
        force=False
        )

    # overwrite_settings_yaml(project_dir, project_name, "ai_search")
    # overwrite_settings_env(project_dir)

    return True
