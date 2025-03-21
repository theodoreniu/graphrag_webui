import os
import time
from dotenv import load_dotenv
from datetime import datetime
from pydantic_settings import BaseSettings

load_dotenv()

app_version = "2.1.0"
graphrag_version = "2.1.0"

app_started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
app_name = "graphrag"

is_debug = os.getenv("DEBUG_MODE") == "true"
update_time = os.getenv("UPDATE_TIME", time.strftime("%Y-%m-%d %H:%M:%S"))

generate_data_vision = "GPT Vision"
generate_data_vision_azure = "Azure Docs"
generate_data_vision_txt = "GPT Vision (as text)"
generate_data_vision_image = "GPT Vision (as image)"
generate_data_vision_di = "Azure AI Document Intelligence (as image)"

pdf_gpt_vision_prompt = """请处理以下PDF页面的截图与原生提取文本，并按以下要求生成最终的准确文字内容：

1. **文字识别**：对该页截图进行OCR文字识别，将图片中的所有文字内容完整提取出来，包括任何图表中的文字。所有输出内容应基于识别结果，不要生成额外的文字或信息。

2. **参考与对比**：对比截图中识别的文字与我提供的原生提取文字。两者可能包含重复内容或在某些部分存在缺失。输出时，请综合参考两者，确保最终文本准确无误。

3. **段落结构**：请按照人类阅读的顺序与逻辑进行段落划分，确保段落组织清晰，逻辑连贯。

4. **表格处理**：如果该页包含表格内容，请在输出时保留表格的结构。可以用缩进、分行等方式展示表格数据，以确保易读性和结构完整性。

5. **不生成多余内容**：所有输出内容必须基于OCR识别与原生提取的文本，不要凭空生成额外内容，仅对识别内容进行整理。

6. **坚持原文**：原文是什么语言，你就生成什么语言，不要翻译，要100%还原。

7. **没有内容返回空字符串**：如果截图中没有任何文字识别处理，请返回空文本。

8. **不要有任务描述的信息**：不要返回你做了什么，你只需要返回整理之后的文字。

---

**示例输入**：

- 截图（附页截图）
- 原生提取文本（如果有）

**输出格式要求**：

- 每段文字应符合人类的阅读顺序，逻辑清晰，段落清晰分明。
- 如包含表格，确保以文本形式呈现出表格的结构，便于理解。

---

本页 PDF 原生文本如下（可能是全部或者部分）：
{page_txt}"""

pdf_gpt_vision_prompt_by_text = """我给你一张截图，是一个产品使用说明书的pdf的某一页的截图，同时，我把这个截图里的所有文字也给你，但是文字的排版和位置可能是错乱的，不是人类阅读产品手册的顺序和位置，但是文字是没有错误的没有多余的。 请你运用视觉能力，全面的观察分析这个截图的每一处排版和每一块文字，然后把文字还原成有结构的、位置正确的文本。把文字放在该放的段落里，也就是人类阅读顺序的位置里。你一定不要增加其他任何的文字，也不要自己创造。一定不要生成任何多余的文字(甚至不要返回你做了什么，你一定只需要返回整理之后的文字)。总之，你要分析图像，然后把没有结构的散乱的文字还原成有结构的文字。 一定不要生成原始文字里没有的文字或者句子。

截图里的所有原始文字如下：
{page_txt}"""

pdf_gpt_vision_prompt_by_image = """给你一张截图，是 PDF 的某一页的截图，请你运用视觉能力，全面的观察分析这个截图的每一处排版和每一块文字，提取和识别文字，然后把文字还原成有结构的、位置正确的文本。把文字放在该放的段落里，也就是人类阅读顺序的位置里。
任务要求：

- 尽可能给我 markdown 文本
- 你一定不要自己创造任何多余的文字
- 不要返回你做了什么，你一定只需要返回整理之后的文字。

截图里的所有原始文字如下：
{page_txt}"""

pdf_gpt_vision_prompt_azure = """我给你发一张pdf的截图，这是azure的说明文档，截图里可能有操作步骤，azure的控制台截图、代码片段、cli命令、参数说明、表格、架构图，请你都详细的说明你看到的所有的东西，并且按照顺序列举。

请注意：
- 如果是文字、代码、cli命令的部分，请不要创造，只是正确完整的识别出来。
- 有些区域可能是控制台截图、流程图、架构图，图片请替换成详细的文字。但是位置不要变，你只需要把你的描述文字替换为原来的控制台截图、架构图、图片。替换前，你需要写明这是关于什么的控制台截图、架构图、命令。
- 你不仅仅要提取控制台截图、流程图、架构图的节点和文字，还要描述流程。你一定要整理成文字关系的详细的流程，而不是markdown的表格或者列表。
- 如果截图中有序号、数字，请不要改动，例如截图可能是某个操作的后续步骤，在当前截图中只是从第二开始，你一定要使用二，而不是一，这样我才能和其他页面的截图对接上。
- 你只需要返回内容，不需要任何额外的信息，比如你不要说：还有什么需要帮助？或者你做了什么，你一定只能返回截图里的内容。
- 如果截图中没有文字，请返回空字符串。
- 你整理的结果要被用作构建知识图谱，所以你的文字描述要完整，不要遗漏任何信息。


同时，我也提取了这个截图的原始文字给你参考，目的是帮助你更准确的提取信息而不至于提取错误的文字，截图里的所有原始文字如下：
{page_txt}"""


class Settings(BaseSettings):
    server_port: int = 20213
    cors_allowed_origins: list = ["*"]  # Edit the list to restrict access.
    root: str = "."
    data: str = "./output"
    community_level: int = 2
    dynamic_community_selection: bool = False
    response_type: str = "Multiple Paragraphs"

    @property
    def website_address(self) -> str:
        return f"http://127.0.0.1:{self.server_port}"


settings = Settings()
