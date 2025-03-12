import os
from libs.find_sources import get_query_sources, get_reference, generate_ref_links
from libs.common import project_path, load_project_env
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import libs.config as config
from graphrag.cli.query import run_local_search, run_global_search, run_drift_search
from dotenv import load_dotenv
import asyncio
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionChunk
import functools
import uuid
import time
from openai.types.chat.chat_completion_chunk import Choice, ChoiceDelta
from graphrag.query.structured_search.local_search.search import LocalSearch
from graphrag.query.structured_search.basic_search.search import BasicSearch
from graphrag.query.structured_search.drift_search.search import DRIFTSearch
from graphrag.query.structured_search.global_search.search import GlobalSearch
from libs import search
from libs.gtypes import ChatCompletionMessageParam, ChatCompletionStreamOptionsParam, ChatCompletionToolParam, ChatQuestionGen
from libs.gtypes import CompletionCreateParamsBase as ChatCompletionRequest, GenerateDataRequest
from libs import consts
from graphrag.query.context_builder.conversation_history import ConversationHistory
import logging
from openai.types import CompletionUsage
from fastapi.encoders import jsonable_encoder
from pathlib import Path
import tempfile

load_dotenv()

app = FastAPI(
    title="GraphRAG WebUI API",
    version=config.app_version,
    terms_of_service="https://github.com/TheodoreNiu/graphrag_webui",
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

basic_search: BasicSearch
local_search: LocalSearch
global_search: GlobalSearch
drift_search: DRIFTSearch

class Item(BaseModel):
    query: str
    project_name: str
    community_level: int = 2
    dynamic_community_selection: bool = False
    query_source: bool = False
    context_data: bool = False


def check_api_key(project_name: str, api_key: str):
    load_project_env(project_name)
    if os.getenv("API_KEY") and os.getenv("API_KEY") != api_key:
        raise Exception("Invalid api-key")

async def init_search_engine(request: ChatCompletionRequest):
    root = project_path(request.project_name),
    data_dir=None,
    root_dir = root[0]
    config, data = await search.load_context(root_dir, data_dir)
    if request.model == consts.INDEX_LOCAL:
        search_engine = await search.load_local_search_engine(config, data)
    elif request.model == consts.INDEX_GLOBAL:
        search_engine = await search.load_global_search_engine(config, data)
    elif request.model == consts.INDEX_DRIFT:
        search_engine = await search.load_drift_search_engine(config, data)
    else:
        search_engine = await search.load_basic_search_engine(config, data)
    return search_engine

def guess_file_type(file_name: str) -> str:
    if file_name.endswith(".pdf"):
        return "pdf"
    elif file_name.endswith(".docx") or file_name.endswith(".doc"):
        return "docx"
    elif file_name.endswith(".xlsx") or file_name.endswith(".xls"):
        return "xlsx"
    elif file_name.endswith(".pptx") or file_name.endswith(".ppt"):
        return "pptx"
    elif file_name.endswith(".csv"):
        return "csv"
    elif file_name.endswith(".txt"):
        return "txt"
    else:
        raise Exception(f"Unsupported file type: {file_name}")
    

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, api_key: str = Header(...)):
    
    try:
        check_api_key(request.project_name, api_key)
        history = request.messages[:-1]
        conversation_history = ConversationHistory.from_list([message.model_dump() for message in history])

        search_engine = await init_search_engine(request)

        if not request.stream:
            return await handle_sync_response(request, search_engine, conversation_history)
        else:
            return await handle_stream_response(request, search_engine, conversation_history)
    except Exception as e:
        logger.error(msg=f"chat_completions error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    
async def handle_sync_response(request, search, conversation_history):
    result = await search.asearch(request.messages[-1].content, conversation_history=conversation_history)
    if isinstance(search, DRIFTSearch):
        response = result.response
        response = response["nodes"][0]["answer"]
    else:
        response = result.response

    # TODO: add reference and modify format
    # reference = get_reference(response)
    # if reference:
    #     response += f"\n{generate_ref_links(reference, request.model)}"
    from openai.types.chat.chat_completion import Choice
    completion = ChatCompletion(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=request.model,
        object="chat.completion",
        choices=[
            Choice(
                index=0,
                finish_reason="stop",
                message=ChatCompletionMessage(
                    role="assistant",
                    content=response
                )
            )
        ],
        usage=CompletionUsage(
            completion_tokens=-1,
            prompt_tokens=result.prompt_tokens,
            total_tokens=-1
        )
    )
    return JSONResponse(content=jsonable_encoder(completion))

async def handle_stream_response(request, search, conversation_history):
    async def wrapper_astream_search():
        token_index = 0
        chat_id = f"chatcmpl-{uuid.uuid4().hex}"
        full_response = ""
        async for token in search.astream_search(request.messages[-1].content, conversation_history):  # 调用原始的生成器
            if token_index == 0:
                token_index += 1
                continue

            chunk = ChatCompletionChunk(
                id=chat_id,
                created=int(time.time()),
                model=request.model,
                object="chat.completion.chunk",
                choices=[
                    Choice(
                        index=token_index - 1,
                        finish_reason=None,
                        delta=ChoiceDelta(
                            role="assistant",
                            content=token
                        )
                    )
                ]
            )
            yield f"data: {chunk.model_dump_json()}\n\n"
            token_index += 1
            full_response += token

        content = ""
        # TODO: add reference and modify format
        # reference = get_reference(full_response)
        # if reference:
        #     content = f"\n{generate_ref_links(reference, request.model)}"
        finish_reason = 'stop'
        chunk = ChatCompletionChunk(
            id=chat_id,
            created=int(time.time()),
            model=request.model,
            object="chat.completion.chunk",
            choices=[
                Choice(
                    index=token_index,
                    finish_reason=finish_reason,
                    delta=ChoiceDelta(
                        role="assistant",
                        # content=result.context_data["entities"].head().to_string()
                        content=content
                    )
                ),
            ],
        )
        yield f"data: {chunk.model_dump_json()}\n\n"
        yield f"data: [DONE]\n\n"

    return StreamingResponse(wrapper_astream_search(), media_type="text/event-stream")

# -----------------------------------------------------------------
@app.post("/api/local_search")
def local_search(item: Item, api_key: str = Header(...)):
    try:
        check_api_key(item.project_name, api_key)

        (response, context_data) = run_local_search(
            root_dir=project_path(item.project_name),
            query=item.query,
            community_level=int(item.community_level),
            response_type="Multiple Paragraphs",
            streaming=False,
            config_filepath=None,
            data_dir=None,
        )

        result = {
            "message": "ok",
            "response": response,
            "query": item.query,
        }

        if item.query_source:
            result["sources"] = get_query_sources(item.project_name, context_data)

        if item.context_data:
            result["context_data"] = context_data

        return result
    except Exception as e:
        return {
            "error": str(e),
        }


# -----------------------------------------------------------------
@app.post("/api/global_search")
def global_search(item: Item, api_key: str = Header(...)):
    try:
        check_api_key(item.project_name, api_key)

        (response, context_data) = run_global_search(
            root_dir=project_path(item.project_name),
            query=item.query,
            community_level=int(item.community_level),
            response_type="Multiple Paragraphs",
            dynamic_community_selection=bool(item.dynamic_community_selection),
            streaming=False,
            config_filepath=None,
            data_dir=None,
        )

        result = {
            "message": "ok",
            "response": response,
            "query": item.query,
        }

        if item.context_data:
            result["context_data"] = context_data

        return result
    except Exception as e:
        return {
            "error": str(e),
        }


@app.post("/api/drift_search")
def drift_search(item: Item, api_key: str = Header(...)):
    try:
        check_api_key(item.project_name, api_key)

        (response, context_data) = run_drift_search(
            root_dir=project_path(item.project_name),
            query=item.query,
            community_level=int(item.community_level),
            streaming=False,
            config_filepath=None,
            data_dir=None,
        )

        result = {
            "message": "ok",
            "response": response,
            "query": item.query,
        }

        if item.context_data:
            result["context_data"] = context_data

        return result
    except Exception as e:
        return {
            "error": str(e),
        }
