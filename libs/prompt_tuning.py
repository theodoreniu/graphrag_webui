

import asyncio
from pathlib import Path
import streamlit as st
import graphrag.api as api
from graphrag.config.load_config import load_config
from graphrag.logger.print_progress import PrintProgressLogger


async def start(base_path:str):

    (
        entity_extraction_prompt,
        entity_summarization_prompt,
        community_summarization_prompt,
    ) = await api.generate_indexing_prompts(
            config=load_config(root_dir=Path(base_path)),
            root=base_path,
            logger=PrintProgressLogger(prefix="Generating prompts..."),
        )

    tab1, tab2, tab3 = st.tabs([
        "🔍 entity_extraction_prompt",
        "📝 entity_summarization_prompt",
        "👥 community_summarization_prompt"
        ])
    with tab1:
        st.markdown("`prompts/entity_extraction.txt`")
        st.text(entity_extraction_prompt)

    with tab2:
        st.markdown("`prompts/summarize_descriptions.txt`")
        st.text(entity_summarization_prompt)

    with tab3:
        st.markdown("`prompts/community_report.txt`")
        st.text(community_summarization_prompt)

    entity_extraction_prompt_path = f"{base_path}/prompts/entity_extraction.txt"
    entity_summarization_prompt_path = f"{base_path}/prompts/summarize_descriptions.txt"
    community_summarization_prompt_path = f"{base_path}/prompts/community_report.txt"
    
    with open(entity_extraction_prompt_path, "wb") as file:
        file.write(entity_extraction_prompt.encode(encoding="utf-8", errors="strict"))
        
    with open(entity_summarization_prompt_path, "wb") as file:
        file.write(entity_summarization_prompt.encode(encoding="utf-8", errors="strict"))
        
    with open(community_summarization_prompt_path, "wb") as file:
        file.write(community_summarization_prompt.encode(encoding="utf-8", errors="strict"))


def prompt_tuning(project_name: str):
    base_path = f"/app/projects/{project_name}"
    
    st.warning("This operation will overwrite your following files, please proceed with caution: \n\n - prompts/entity_extraction.txt \n\n - prompts/summarize_descriptions.txt \n\n - prompts/community_report.txt")
    
    if st.button('Start Tuning ', key=f"prompt_tuning_{project_name}", icon="🚀"):
        with st.spinner("Running..."):
            asyncio.run(start(base_path))
