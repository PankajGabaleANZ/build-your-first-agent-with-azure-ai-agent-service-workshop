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

import glob
vector_files = glob.glob("/workspaces/build-your-first-agent-with-azure-ai-agent-service-workshop/files/*") 

INSTRUCTIONS_FILE = "instructions/instructions_file_search.txt"
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def send_email(subject, body):
    """
    This function is used to send an email to the users if they have added an expense. Send the expense checking the expense and send the email to user if the expense is compliant or not.

    """
    try:
        print("Sending email...to the user")
        # # Usage Example:
        sender_email = "gabalepankaj@gmail.com"
        receiver_email = "gabalepankaj@hotmail.com"
        subject = subject
        body = body
        smtp_server = "smtp.gmail.com"  # For Gmail
        smtp_port = 587  # SMTP port for Gmail
        sender_password = "wqil wwlp laxm ndud"  # Make sure to use an App Password if using Gmail

        # send_email(sender_email, receiver_email, subject, body, smtp_server, smtp_port, sender_password)
        # Create the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Set up the server
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        
        # Login to the server
        server.login(sender_email, sender_password)
        
        # Send the email
        server.sendmail(sender_email, receiver_email, msg.as_string())
        
        # Quit the server connection
        server.quit()
        
        print("Email sent successfully!")
        return body
    except Exception as e:
        print("Email Sent Failed")
        print(f"Error: {e}")
        

functions = AsyncFunctionTool(
    {
        sales_data.async_fetch_sales_data_using_sqlite_query,
        employee_data.async_fetch_employee_data_using_sqlite_query,
        send_email,
    }
)

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
            files=vector_files,
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
    
    # Get database schema information
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

        # Try to get existing agent first
        try:
            existing_agents = await project_client.agents.list_agents()
            agent = next((a for a in existing_agents if a.name == AGENT_NAME), None)
        except Exception:
            agent = None
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        agent_name_with_timestamp = f"{AGENT_NAME}_{timestamp}"
        # Create new agent if not found
        if not agent:
            print("Creating agent...")
            agent = await project_client.agents.create_agent(
                model=API_DEPLOYMENT_NAME,
                name=agent_name_with_timestamp,
                instructions=instructions,
                toolset=toolset,
                temperature=TEMPERATURE,
                headers={"x-ms-enable-preview": "true"},
            )
            print(f"Created agent, ID: {agent.id}")
        else:
            print(f"Using existing agent, ID: {agent.id}")
        #Sleep for 10 seconds to allow the agent to be created
        import time
        time.sleep(10)
        print("Creating thread...")
        thread = await project_client.agents.create_thread()
        print(f"Created thread, ID: {thread.id}")

        return agent, thread

    except Exception as e:
        logger.error("An error occurred initializing the agent: %s", str(e))
        logger.error("Please ensure you've enabled an instructions file.")
        return None, None

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
        if not attachments:
            print("user has not attached any files")

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
    try:
        agent, thread = await initialize()
        if agent is None or thread is None:
            await cl.Message(content="Initialization failed, exiting program.").send()
            return
        
        # Store agent and thread in the user session
        cl.user_session.set("agent", agent)
        cl.user_session.set("thread", thread)
        
        await cl.Message(content="Agent initialized. You can now ask questions.").send()
    except Exception as e:
        await cl.Message(content=f"Error during initialization: {e}").send()

from pathlib import Path
import shutil
def debug_file_paths(files: list[str]):
    """Debug function to check file paths."""
    for file in files:
        path = Path(file)
        print(f"File path: {path}")
        print(f"  Exists: {path.exists()}")
        print(f"  Is file: {path.is_file()}")
        print(f"  Absolute: {path.absolute()}")
        print(f"  Size: {path.stat().st_size if path.exists() else 'N/A'}")
    return len([f for f in files if Path(f).exists()])

from pathlib import Path
import shutil

@cl.on_message
async def on_message(message: cl.Message):
    """Handle messages and file uploads in Chainlit."""
    agent = cl.user_session.get("agent")
    thread = cl.user_session.get("thread")

    print(f"Agent in session: {agent.id if agent else None}")
    print(f"Thread in session: {thread.id if thread else None}")

    if not agent or not thread:
        await cl.Message(content="Agent or thread not initialized. Please refresh the page to start a new chat.").send()
        return

    uploaded_files = []
    save_dir = Path("files")  
    save_dir.mkdir(parents=True, exist_ok=True)

    file_contents = []  # Store file contents to append to the message

    # Handle file uploads
    if message.elements:
        for element in message.elements:
            if element.type == "file":
                file_path = save_dir / element.name

                try:
                    shutil.copyfile(element.path, file_path)
                    uploaded_files.append(str(file_path))

                    # Read file contents
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
                        file_text = file.read()
                        file_contents.append(f"**File: {element.name}**\n{file_text}")

                    print(f"📂 File saved: {file_path}")
                except Exception as e:
                    print(f"Error saving file: {e}")
                    await cl.Message(content=f"⚠️ Error saving file: {element.name}").send()
                    continue

    # Combine user message with file contents
    combined_content = message.content
    if file_contents:
        combined_content += "\n\n" + "\n\n".join(file_contents)

    # Forward the message to AI agent
    await post_message(
        agent=agent,
        thread_id=thread.id,
        content=combined_content,  # Pass combined user message + file content
        thread=thread,
        uploaded_files=uploaded_files,
    )


@cl.on_chat_end
async def on_chat_end():
    agent = cl.user_session.get("agent")
    thread = cl.user_session.get("thread")
    if agent and thread:
        await cleanup(agent,thread)