import streamlit as st
import os
from streamlit_ace import st_ace
from libs.common import list_files_and_sizes
import libs.config as config

from graphrag.prompts.index.extract_graph import GRAPH_EXTRACTION_PROMPT
from graphrag.prompts.index.extract_claims import EXTRACT_CLAIMS_PROMPT
from graphrag.prompts.index.community_report import (
    COMMUNITY_REPORT_PROMPT,
)

from graphrag.prompts.index.summarize_descriptions import SUMMARIZE_PROMPT
from graphrag.prompts.query.drift_search_system_prompt import DRIFT_LOCAL_SYSTEM_PROMPT
from graphrag.prompts.query.global_search_knowledge_system_prompt import (
    GENERAL_KNOWLEDGE_INSTRUCTION,
)
from graphrag.prompts.query.global_search_map_system_prompt import MAP_SYSTEM_PROMPT
from graphrag.prompts.query.global_search_reduce_system_prompt import (
    REDUCE_SYSTEM_PROMPT,
)
from graphrag.prompts.query.local_search_system_prompt import LOCAL_SEARCH_SYSTEM_PROMPT
from graphrag.prompts.query.question_gen_system_prompt import QUESTION_SYSTEM_PROMPT


def get_setting_file(file_path: str, default_prompt: str=""):
    if not os.path.exists(file_path):
        return default_prompt

    with open(file_path, "r") as f:
        prompt = f.read()
        return prompt


def setting_editor(
    project_name: str,
    file_path: str,
    default_value: str="",
    language="yaml",
    read_only: bool=False,
):
    settings_file = f"/app/projects/{project_name}/{file_path}"

    settings = get_setting_file(settings_file, default_value)

    try:
        new_settings = st_ace(
            settings,
            theme="chaos",
            language=language,
            height=500,
            auto_update=True,
            wrap=True,
            show_gutter=True,
            readonly=read_only,
            show_print_margin=True,
            key=f"{project_name}-{file_path}",
        )

        if not read_only and st.button(
            "Save", key=f"{project_name}-{file_path}-btn", icon="💾"
        ):
            with open(settings_file, "w") as f:
                f.write(new_settings)
            st.success(f"Settings saved: {file_path}")
    except Exception as e:
        st.error(f"Error: {e}")

    if not read_only and st.button(
        "Restore", key=f"{project_name}-{file_path}-btn-restore", icon="🔄"
    ):
        with open(settings_file, "w") as f:
            f.write(default_value)
        st.success(f"Settings restored: {file_path}, please refresh the page.")


def list_and_download_files(files_path: str, title: str="Files"):
    if not os.path.exists(files_path):
        os.makedirs(files_path)

    files = list_files_and_sizes(files_path)
    st.markdown(f"{title}: `{len(files)}`")
    if len(files) > 0:
        for file in files:
            with open(file[1], "rb") as f:
                st.download_button(
                    label=f"📄 {file[0]} `{file[2]}`",
                    data=f,
                    file_name=file[0],
                    key=f"{files_path}-input-{file[0]}",
                )


def set_settings(project_name: str, read_only=False):

    if not read_only:
        config_link = "https://microsoft.github.io/graphrag/config/yaml/"
        st.markdown(f"Default Configuration: [{config_link}]({config_link})")

    default_settings = ""
    with open("/app/template/setting_lancedb.yaml", "r") as t:
        default_settings = t.read()
    (
        tab0,
        tab1,
        tab3,
        tab4,
        tab5,
        tab6,
        tab7,
        tab8,
        tab9,
        tab10,
        tab11,
        tab12,
        tab13,
        tab14,
        tab15,
    ) = st.tabs(
        [
            "📄 .env",
            "📄 settings.yaml",
            "📄 claim_extraction",
            "📄 community_report",
            "📄 entity_extraction",
            "📄 summarize_descriptions",
            "📄 drift_search_system_prompt",
            "📄 global_search_map_system_prompt",
            "📄 global_search_reduce_system_prompt",
            "📄 global_search_knowledge_system_prompt",
            "📄 local_search_system_prompt",
            "📄 question_gen_system_prompt",
            "📄 pdf_gpt_vision_prompt",
            "📄 pdf_gpt_vision_prompt_by_text",
            "📄 pdf_gpt_vision_prompt_by_image",
        ]
    )
    with tab0:
        if read_only:
            st.write("This is a hidden tab for test.")
        else:
            setting_editor(
                project_name,
                ".env",
                language="sh",
                read_only=read_only,
            )
    with tab1:
        setting_editor(
            project_name,
            "settings.yaml",
            default_value=default_settings,
            language="yaml",
            read_only=read_only,
        )
    with tab3:
        setting_editor(
            project_name,
            "prompts/claim_extraction.txt",
            default_value=EXTRACT_CLAIMS_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab4:
        setting_editor(
            project_name,
            "prompts/community_report.txt",
            default_value=COMMUNITY_REPORT_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab5:
        setting_editor(
            project_name,
            "prompts/entity_extraction.txt",
            default_value=GRAPH_EXTRACTION_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab6:
        setting_editor(
            project_name,
            "prompts/summarize_descriptions.txt",
            default_value=SUMMARIZE_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab7:
        setting_editor(
            project_name,
            "prompts/drift_search_system_prompt.txt",
            default_value=DRIFT_LOCAL_SYSTEM_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab8:
        setting_editor(
            project_name,
            "prompts/global_search_map_system_prompt.txt",
            default_value=MAP_SYSTEM_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab9:
        setting_editor(
            project_name,
            "prompts/global_search_reduce_system_prompt.txt",
            default_value=REDUCE_SYSTEM_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab10:
        setting_editor(
            project_name,
            "prompts/global_search_knowledge_system_prompt.txt",
            default_value=GENERAL_KNOWLEDGE_INSTRUCTION,
            language="plain_text",
            read_only=read_only,
        )
    with tab11:
        setting_editor(
            project_name,
            "prompts/local_search_system_prompt.txt",
            default_value=LOCAL_SEARCH_SYSTEM_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab12:
        setting_editor(
            project_name,
            "prompts/question_gen_system_prompt.txt",
            default_value=QUESTION_SYSTEM_PROMPT,
            language="plain_text",
            read_only=read_only,
        )
    with tab13:
        setting_editor(
            project_name,
            "prompts/pdf_gpt_vision_prompt.txt",
            default_value=config.pdf_gpt_vision_prompt,
            language="plain_text",
            read_only=read_only,
        )
    with tab14:
        setting_editor(
            project_name,
            "prompts/pdf_gpt_vision_prompt_by_text.txt",
            default_value=config.pdf_gpt_vision_prompt_by_text,
            language="plain_text",
            read_only=read_only,
        )
    with tab15:
        setting_editor(
            project_name,
            "prompts/pdf_gpt_vision_prompt_by_image.txt",
            default_value=config.pdf_gpt_vision_prompt_by_image,
            language="plain_text",
            read_only=read_only,
        )
