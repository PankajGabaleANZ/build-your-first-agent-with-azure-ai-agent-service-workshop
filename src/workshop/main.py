import asyncio
import logging
import os
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import (
    Agent,
    AgentThread,
    AsyncFunctionTool,
    AsyncToolSet,
    CodeInterpreterTool,FileSearchTool,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from sales_data import SalesData
from employee_data import EmployeeData
from stream_event_handler import StreamEventHandler
from utilities import Utilities

import chainlit as cl

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

load_dotenv()

AGENT_NAME = "Contoso Sales Agent"
API_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")
PROJECT_CONNECTION_STRING = os.environ["PROJECT_CONNECTION_STRING"]
MAX_COMPLETION_TOKENS = 4096
MAX_PROMPT_TOKENS = 10240
TEMPERATURE = 0.1
TOP_P = 0.1

toolset = AsyncToolSet()
sales_data = SalesData()
employee_data = EmployeeData()
utilities = Utilities()

project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=PROJECT_CONNECTION_STRING,
)

functions = AsyncFunctionTool(
    {
        sales_data.async_fetch_sales_data_using_sqlite_query,
        employee_data.async_fetch_employee_data_using_sqlite_query,
    }
)

INSTRUCTIONS_FILE = "instructions/instructions_bing_grounding.txt"
TENTS_DATA_SHEET_FILE = "files/Contoso_Product_Information.csv"

async def add_agent_tools():
    """Add tools for the agent."""
    global toolset
    if len(toolset._tools) == 0:  # Corrected line
        toolset.add(functions)
        code_interpreter = CodeInterpreterTool()
        toolset.add(code_interpreter)

        #dd the tents data sheet to a new vector data store
        vector_store = await utilities.create_vector_store(
            project_client,
            files=["instructions/instructions_bing_grounding.txt"],
            vector_name_name="Contoso Product Information Vector Store",
        )
        file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])
        toolset.add(file_search_tool)

        # Add the Bing grounding tool
        # bing_connection = await project_client.connections.get(connection_name=BING_CONNECTION_NAME)
        # bing_grounding = BingGroundingTool(connection_id=bing_connection.id)
        # toolset.add(bing_grounding)

async def initialize() -> tuple[Agent, AgentThread]:
    """Initialize the agent with the sales data schema and instructions."""

    await add_agent_tools()

    await sales_data.connect()
    await employee_data.connect()
    sales_schema_string = await sales_data.get_database_info()
    employee_schema_string = await employee_data.get_database_info()
    database_schema_string = f"{sales_schema_string}\n\n{employee_schema_string}"
    try:
        env = os.getenv("ENVIRONMENT", "local")
        INSTRUCTIONS_FILE_PATH = f"{'src/workshop/' if env == 'container' else ''}{INSTRUCTIONS_FILE}"

        with open(INSTRUCTIONS_FILE_PATH, "r", encoding="utf-8", errors="ignore") as file:
            instructions = file.read()

        instructions = instructions.replace("{database_schema_string}", sales_schema_string)
        instructions = instructions.replace("{employee_schema_string}", employee_schema_string)

        print("Creating agent...")
        agent = await project_client.agents.create_agent(
            model=API_DEPLOYMENT_NAME,
            name=AGENT_NAME,
            instructions=instructions,
            toolset=toolset,
            temperature=TEMPERATURE,
            headers={"x-ms-enable-preview": "true"},
        )
        print(f"Created agent, ID: {agent.id}")

        print("Creating thread...")
        thread = await project_client.agents.create_thread()
        print(f"Created thread, ID: {thread.id}")

        return agent, thread

    except Exception as e:
        logger.error("An error occurred initializing the agent: %s", str(e))
        logger.error("Please ensure you've enabled an instructions file.")
        return None, None
    
async def search_vector_store(query: str, vector_store):
    """Search the Azure OpenAI vector store for relevant information."""
    utilities.log_msg_purple(f"Searching vector store for query: {query}")

    response = await project_client.agents.vector_search(
        vector_store_id=vector_store.id, query=query, top_k=3
    )

    if response.matches:
        matched_content = "\n".join([match.content for match in response.matches])
        return f"Here’s what I found:\n\n{matched_content}"
    
    return None

async def cleanup(agent: Agent, thread: AgentThread) -> None:
    """Cleanup the resources."""
    if agent and thread:
        await project_client.agents.delete_thread(thread.id)
        await project_client.agents.delete_agent(agent.id)
    await sales_data.close()
    await employee_data.close()


async def post_message(thread_id: str, content: str, agent: Agent, thread: AgentThread, uploaded_files: list[str] = []) -> None:
    """Post a message to the AI agent, including any user-uploaded attachments."""
    try:
        attachments = []

        # Convert file paths into attachment format
        for file_path in uploaded_files:
            attachments.append({
                "file_id": file_path,  # Assuming file_id is the saved path
                "file_name": os.path.basename(file_path),
            })

        await project_client.agents.create_message(
            thread_id=thread_id,
            role="user",
            content=content,
            attachments=attachments,  # Attach user files
        )

        stream = await project_client.agents.create_stream(
            thread_id=thread.id,
            assistant_id=agent.id,
            event_handler=StreamEventHandler(functions=functions, project_client=project_client, utilities=utilities),
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            max_prompt_tokens=MAX_PROMPT_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            instructions=agent.instructions,
        )

        full_response = ""  # Accumulate the response here

        async with stream as s:
            async for event in s:
                if isinstance(event, tuple):
                    event_type, event_data, _ = event
                    if event_type == "thread.message.delta":
                        delta = event_data.get("delta")
                        if delta and "content" in delta:
                            content_list = delta["content"]
                            for item in content_list:
                                if item.get("type") == "text" and "text" in item:
                                    text_value = item["text"].get("value")
                                    if text_value:
                                        full_response += text_value  # Accumulate
                else:
                    if hasattr(event, "type"):
                        if event.type == "text":
                            full_response += event.content  # Accumulate
                        elif event.type == "tool_call":
                            await cl.Message(content=f"Tool call: {event.name}").send()
                        elif event.type == "tool_response":
                            await cl.Message(content=f"Tool response: {event.content}").send()
                    else:
                        print(f"Unhandled event: {event}")
            await s.until_done()

        await cl.Message(content=full_response).send()  # Send the complete response.

    except Exception as e:
        utilities.log_msg_purple(f"An error occurred posting the message: {str(e)}")
        await cl.Message(content=f"Error occurred: {e}").send()
        await cleanup(agent, thread)


@cl.on_chat_start
async def main():
    """Chainlit main function."""
    if cl.user_session.get("agent") is None:
        agent, thread = await initialize()
        if agent is None or thread is None:
            await cl.Message(content="Initialization failed, exiting program.").send()
            return
        cl.user_session.set("agent", agent)
        cl.user_session.set("thread", thread)
        await cl.Message(content="Agent initialized. You can now ask questions.").send()
    else:
        await cl.Message(content="Existing Agent Found. You can now ask questions.").send()

from pathlib import Path
import shutil

@cl.on_message
async def on_message(message: cl.Message):
    """Handle messages and file uploads in Chainlit."""
    agent = cl.user_session.get("agent")
    thread = cl.user_session.get("thread")

    if not agent or not thread:
        await cl.Message(content="Agent or thread not initialized.").send()
        return

    uploaded_files = []

    # 🔍 Check if message has file attachments
    if message.elements:
        save_dir = Path("files")  # Define local save directory
        save_dir.mkdir(parents=True, exist_ok=True)  # Create if not exists

        for element in message.elements:
            if element.type == "file":
                file_path = save_dir / Path(element.path).name  # Save file in local folder
                shutil.copy(element.path, file_path)  # Copy file from Chainlit temp to local
                uploaded_files.append(str(file_path))  # Collect saved file path

                print(f"📂 File saved: {file_path}")

        # ✅ Upload saved files to the vector store
        vector_store = await utilities.create_vector_store(
            project_client, uploaded_files, "UserUploadedVectorStore"
        )

        # Save vector store ID for future searches
        cl.user_session.set("vector_store", vector_store)

        await cl.Message(content=f"📁 {len(uploaded_files)} files uploaded and indexed.").send()

    # 🔍 Search vector store before calling agent
    vector_store = cl.user_session.get("vector_store")
    if vector_store:
        answer = await search_vector_store(message.content, vector_store)
        if answer:
            await cl.Message(content=answer).send()
            return  # Avoid unnecessary AI processing if we have an answer

    # 🚀 Forward the message to AI agent if no answer was found in vector DB
    await post_message(
        agent=agent,
        thread_id=thread.id,
        content=message.content,
        thread=thread,
        uploaded_files=uploaded_files,
    )

@cl.on_chat_end
async def on_chat_end():
    agent = cl.user_session.get("agent")
    thread = cl.user_session.get("thread")
    if agent and thread:
        await cleanup(agent,thread)