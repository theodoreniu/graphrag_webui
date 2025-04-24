from typing import Optional, Dict, List, Union, Literal, Any

from pydantic import BaseModel

class GenerateDataFileItem(BaseModel):
    file_name: str
    file_url: str
    file_type: Optional[str]


class GenerateDataRequest(BaseModel):
    project_name: str
    is_local_directory: bool
    files: Optional[List[GenerateDataFileItem]]
    directory: Optional[str]
    


class ChatCompletionMessageParam(BaseModel):
    content: str
    role: str = "user"


class ResponseFormat(BaseModel):
    type: str


class ChatCompletionStreamOptionsParam(BaseModel):
    enable: bool


class ChatCompletionToolParam(BaseModel):
    name: str
    description: str


class CompletionCreateParamsBase(BaseModel):
    project_name: str
    community_level: int
    messages: List[ChatCompletionMessageParam]
    system_prompt: Optional[str] = None
    model: str
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, int]] = None
    logprobs: Optional[bool] = None
    max_tokens: Optional[int] = None
    n: Optional[int] = None
    parallel_tool_calls: bool = False
    presence_penalty: Optional[float] = None
    response_format: ResponseFormat = ResponseFormat(type="text")
    seed: Optional[int] = None
    service_tier: Optional[Literal["auto", "default"]] = None
    stop: Optional[Union[str, List[str]]] = None
    stream: Optional[bool] = False
    stream_options: Optional[Dict] = None
    temperature: Optional[float] = 0.0
    tools: List[ChatCompletionToolParam] = None
    top_logprobs: Optional[int] = None
    top_p: Optional[float] = 1.0
    user: Optional[str] = None
    generate_question: Optional[bool] = False
    generate_question_count: Optional[int] = 5
    generate_question_prompt: Optional[str] = None
    show_reference: Optional[bool] = False

    def llm_chat_params(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "seed": self.seed
        }


class ChatQuestionGen(BaseModel):
    messages: List[ChatCompletionMessageParam]
    model: str
    max_tokens: Optional[int] = None
    temperature: Optional[float] = 0.0
    n: Optional[int] = None


class Model(BaseModel):
    id: str
    object: Literal["model"]
    created: int
    owned_by: str


class ModelList(BaseModel):
    object: Literal["list"] = "list"
    data: List[Model]