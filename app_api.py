import os
from libs.find_sources import get_query_sources, get_reference, generate_ref_links
from libs.common import project_path, load_project_env
from graphrag.query.llm.get_client import get_llm, get_text_embedder
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
from graphrag.query.question_gen.local_gen import LocalQuestionGen
from libs import search
from libs.search import reformat_context_data
from libs.gtypes import ChatCompletionMessageParam, ChatCompletionStreamOptionsParam, ChatCompletionToolParam, ChatQuestionGen
from libs.gtypes import CompletionCreateParamsBase as ChatCompletionRequest, GenerateDataRequest
from libs import consts
from graphrag.query.context_builder.conversation_history import ConversationHistory
import logging
from openai.types import CompletionUsage
from fastapi.encoders import jsonable_encoder
from pathlib import Path
import tiktoken
import json
import re

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
    root = project_path(request.project_name)
    data_dir=None
    config, data = await search.load_context(root, data_dir)
    system_prompt = request.system_prompt
    if request.model == consts.INDEX_LOCAL:
        search_engine = await search.load_local_search_engine(config, data, system_prompt)
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
    
async def local_question_gen(request, context_data: dict):
    root = project_path(request.project_name)
    data_dir=None
    config, data = await search.load_context(root, data_dir)
    llm = get_llm(config)
    token_encoder = tiktoken.get_encoding(config.encoding_model)
    system_prompt = request.generate_question_prompt
    question_gen = LocalQuestionGen(llm=llm, token_encoder=token_encoder, context_builder=None, context_builder_params=None, system_prompt=system_prompt)
    question_history = [user_message.content for user_message in request.messages if user_message.role == "user"]
    questions = await question_gen.agenerate(
        question_history=question_history,
        context_data=context_data,
        question_count=request.generate_question_count,
    )
    return questions.response

async def attach_question_gen(base_response: dict, request, context_data: dict) -> dict:
    if not context_data or not isinstance(context_data, dict):
        context_data = {}
    if request.generate_question and request.model == consts.INDEX_LOCAL:
        try:
            question_gen = await local_question_gen(request, context_data)
            base_response['question_gen'] = question_gen
        except Exception as e:
            logger.error(f"Error in question generation: {e}")
            base_response['question_gen'] = "Error in question generation"
    return base_response

def handle_reference(request:ChatCompletionRequest, response: str) -> str:
    if not request.show_reference:
        # Remove the reference part from the response
        cleaned_text = re.sub(r'\[Data: [^\]]+\]', '', response)
        return cleaned_text.strip()
    else:
        return response

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

    # print context_data
    # context_data = reformat_context_data(result.context_data)  # type: ignore
    # logger.debug(f"context_data: {context_data}")

    if isinstance(search, DRIFTSearch):
        response = result.response
        response = response["nodes"][0]["answer"]
    else:
        response = result.response

    response = handle_reference(request, response) 
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

    base_response = completion.to_dict()
    final_response = await attach_question_gen(base_response, request, result.context_data)
    return JSONResponse(content=jsonable_encoder(final_response))

async def handle_stream_response(request, search, conversation_history):
    async def wrapper_astream_search():
        chat_id = f"chatcmpl-{uuid.uuid4().hex}"
        context_data = None
        tokens = []
        async for token in search.astream_search(request.messages[-1].content, conversation_history):  # 调用原始的生成器
            if context_data is None:
                context_data = token  # capture context info on the first token
                continue
            tokens.append(token)
            chunk = create_chunk(chat_id, tokens, request.model)
            yield f"data: {chunk.model_dump_json()}\n\n"

        # TODO: add reference and modify format
        # reference = get_reference(full_response)
        # if reference:
        #     content = f"\n{generate_ref_links(reference, request.model)}"
        finish_reason = 'stop'
        chunk = create_chunk(chat_id, tokens, request.model)
        chunk.choices[0].finish_reason = finish_reason
        chunk.choices[0].delta.content = handle_reference(request, "".join(tokens))
        chunk.choices[0].index = len(tokens)
        base_response = chunk.to_dict()  # Build a final response dict if necessary
        final_response = await attach_question_gen(base_response, request, context_data)
        yield f"data: {json.dumps(final_response)}\n\n"
        yield f"data: [DONE]\n\n"

    return StreamingResponse(wrapper_astream_search(), media_type="text/event-stream")

def create_chunk(chat_id, tokens, model):
    # Minimal helper to form a ChatCompletionChunk from tokens.
    assert tokens, "Expected at least one token in the tokens list"
    return ChatCompletionChunk(
        id=chat_id,
        created=int(time.time()),
        model=model,
        object="chat.completion.chunk",
        choices=[Choice(index=len(tokens)-1, finish_reason=None, delta=ChoiceDelta(role="assistant", content=tokens[-1]))]
    )

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
