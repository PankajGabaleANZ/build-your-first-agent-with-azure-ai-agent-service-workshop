from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
import asyncio
from dotenv import load_dotenv
import os
import shutil
import fitz
import os
import uuid
import chainlit as cl
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from azure.ai.projects.models import (
    Agent,
    AgentThread,
    AsyncFunctionTool,
    AsyncToolSet,
    CodeInterpreterTool,FileSearchTool,BingGroundingTool
)


toolset = AsyncToolSet()

load_dotenv()

# Initialize environment variables
API_KEY = os.getenv("API_KEY")
PROJECT_CONNECTION_STRING = os.getenv("PROJECT_CONNECTION_STRING")
BING_CONNECTION_NAME = os.getenv("BING_CONNECTION_NAME")
MODEL_DEPLOYMENT_NAME = os.getenv("MODEL_DEPLOYMENT_NAME")
MODEL_API_VERSION = os.getenv("MODEL_API_VERSION")
AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")

###############################################################################
#                              Azure OpenAI Client
###############################################################################
az_model_client = AzureOpenAIChatCompletionClient(
    azure_deployment=MODEL_DEPLOYMENT_NAME,
    model=MODEL_DEPLOYMENT_NAME,
    api_version=MODEL_API_VERSION,
    azure_endpoint=AZURE_ENDPOINT,
    api_key=API_KEY
)

###############################################################################
#                              AI Project Client
###############################################################################
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=PROJECT_CONNECTION_STRING,
)

# Retrieve the Bing connection
bing_connection = project_client.connections.get(connection_name=BING_CONNECTION_NAME)
conn_id = bing_connection.id
import glob
vector_files = glob.glob("/workspaces/build-your-first-agent-with-azure-ai-agent-service-workshop/files/*") 



###############################################################################
#                               BING QUERY TOOLS
###############################################################################
async def stock_price_trends_tool(stock_name: str) -> str:
    """
    A dedicated Bing call focusing on real-time stock prices,
    changes over the last few months for 'stock_name'.
    """
    print(f"[stock_price_trends_tool] Fetching stock price trends for {stock_name}...")
    bing = BingGroundingTool(connection_id=conn_id)
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="stock_price_trends_tool_agent",
        instructions=(
            f"Focus on retrieving real-time stock prices, changes over the last few months, "
            f"and summarize market trends for {stock_name}."
        ),
        tools=bing.definitions,
        headers={"x-ms-enable-preview": "true"}
    )

    # Create a new thread and send the user query
    thread = project_client.agents.create_thread()
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=f"Please get stock price trends data for {stock_name}."
    )
    # Process the run
    run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
    messages = project_client.agents.list_messages(thread_id=thread.id)

    # Clean up
    project_client.agents.delete_agent(agent.id)

    # Return the Bing result
    return messages["data"][0]["content"][0]["text"]["value"]


async def news_analysis_tool(stock_name: str) -> str:
    """
    A dedicated Bing call focusing on the latest news for 'stock_name'.
    """
    print(f"[news_analysis_tool] Fetching news for {stock_name}...")
    bing = BingGroundingTool(connection_id=conn_id)
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="news_analysis_tool_agent",
        instructions=f"Focus on the latest news highlights for the stock {stock_name}.",
        tools=bing.definitions,
        headers={"x-ms-enable-preview": "true"}
    )

    thread = project_client.agents.create_thread()
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=f"Retrieve the latest news articles and summaries about {stock_name}."
    )
    await asyncio.sleep(0.5)  
    run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
    messages = project_client.agents.list_messages(thread_id=thread.id)

    # Clean up
    project_client.agents.delete_agent(agent.id)

    return messages["data"][0]["content"][0]["text"]["value"]


async def market_sentiment_tool(stock_name: str) -> str:
    """
    A dedicated Bing call focusing on overall market sentiment
    for 'stock_name'.
    """
    print(f"[market_sentiment_tool] Fetching sentiment for {stock_name}...")
    bing = BingGroundingTool(connection_id=conn_id)
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="market_sentiment_tool_agent",
        instructions=(
            f"Focus on analyzing general market sentiment regarding {stock_name}."
        ),
        tools=bing.definitions,
        headers={"x-ms-enable-preview": "true"}
    )
    await asyncio.sleep(0.7)  
    thread = project_client.agents.create_thread()
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=(
            f"Gather market sentiment, user opinions, and overall feeling about {stock_name}."
        )
    )
    run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
    messages = project_client.agents.list_messages(thread_id=thread.id)

    # Clean up
    project_client.agents.delete_agent(agent.id)

    return messages["data"][0]["content"][0]["text"]["value"]


async def analyst_reports_tool(stock_name: str) -> str:
    """
    A dedicated Bing call focusing on analyst reports
    for 'stock_name'.
    """
    print(f"[analyst_reports_tool] Fetching analyst reports for {stock_name}...")
    bing = BingGroundingTool(connection_id=conn_id)
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="analyst_reports_tool_agent",
        instructions=(
            f"Focus on any relevant analyst reports or professional analyses about {stock_name}."
        ),
        tools=bing.definitions,
        headers={"x-ms-enable-preview": "true"}
    )

    thread = project_client.agents.create_thread()
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=(f"Find recent analyst reports, price targets, or professional opinions on {stock_name}.")
    )
    run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
    messages = project_client.agents.list_messages(thread_id=thread.id)

    # Clean up
    project_client.agents.delete_agent(agent.id)

    return messages["data"][0]["content"][0]["text"]["value"]

async def expert_opinions_tool(stock_name: str) -> str:
    """
    A dedicated Bing call focusing on expert or industry leaders' opinions
    for 'stock_name'.
    """
    print(f"[expert_opinions_tool] Fetching expert opinions for {stock_name}...")
    bing = BingGroundingTool(connection_id=conn_id)
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="expert_opinions_tool_agent",
        instructions=(
            f"Focus on industry expert or thought leader opinions regarding {stock_name}."
        ),
        tools=bing.definitions,
        headers={"x-ms-enable-preview": "true"}
    )

    thread = project_client.agents.create_thread()
    message = project_client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=(f"Collect expert opinions or quotes about {stock_name}.")
    )
    run = project_client.agents.create_and_process_run(thread_id=thread.id, assistant_id=agent.id)
    messages = project_client.agents.list_messages(thread_id=thread.id)

    # Clean up
    project_client.agents.delete_agent(agent.id)

    return messages["data"][0]["content"][0]["text"]["value"]

def read_pdf(default_path: str, file_name: str) -> str:
    """
    Reads a PDF file and extracts its text content.

    Parameters:
        default_path (str): The directory path where the PDF file is stored.
        file_name (str): The name of the PDF file to be read.

    Returns:
        str: Extracted text content from the PDF.
    """
    file_path = os.path.join(default_path, file_name)

    if not os.path.exists(file_path):
        return f"Error: The file '{file_name}' does not exist in '{default_path}'."

    try:
        with fitz.open(file_path) as pdf:
            text = "\n".join([page.get_text("text") for page in pdf])  # Extract text from all pages
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

# -- Trend Data
async def stock_price_trends_agent(stock_name: str) -> str:
    """Agent function for 'stock trends', calls stock_price_trends_tool."""
    return await stock_price_trends_tool(stock_name)

# -- News
async def news_analysis_agent(stock_name: str) -> str:
    """Agent function for 'latest news', calls news_analysis_tool."""
    return await news_analysis_tool(stock_name)


async def market_sentiment_agent(stock_name: str) -> str:
    """Agent function for 'market sentiment', calls market_sentiment_tool."""
    return await market_sentiment_tool(stock_name)

# -- Analyst Reports

async def analyst_reports_agent(stock_name: str) -> str:
    """Agent function for 'analyst reports', calls analyst_reports_tool."""
    return await analyst_reports_tool(stock_name)

# -- Expert Opinions

async def expert_opinions_agent(stock_name: str) -> str:
    """Agent function for 'expert opinions', calls expert_opinions_tool."""
    return await expert_opinions_tool(stock_name)



stock_trends_agent_assistant = AssistantAgent(
    name="stock_trends_agent",
    model_client=az_model_client,
    tools=[stock_price_trends_agent],
    system_message=(
        "You are the Stock Price Trends Agent. "
        "You fetch and summarize stock prices, changes over the last few months, and general market trends. "
        "Do NOT provide any final investment decision."
    )
)

news_agent_assistant = AssistantAgent(
    name="news_agent",
    model_client=az_model_client,
    tools=[news_analysis_agent],
    system_message=(
        "You are the News Agent. "
        "You retrieve and summarize the latest news stories related to the given stock. "
        "Do NOT provide any final investment decision."
    )
)

sentiment_agent_assistant = AssistantAgent(
    name="sentiment_agent",
    model_client=az_model_client,
    tools=[
        market_sentiment_agent,
        analyst_reports_agent,
        expert_opinions_agent
    ],
    system_message=(
        "You are the Market Sentiment Agent. "
        "You gather overall market sentiment, relevant analyst reports, and expert opinions. "
        "Do NOT provide any final investment decision."
    )
)

decision_agent_assistant = AssistantAgent(
    name="decision_agent",
    model_client=az_model_client,
    # The final agent typically calls the 'investment_decision_agent' to
    # synthesize all the data. If you want it to call the other tools directly,
    # you can also add them here. But typically we rely on the round-robin approach.
    # tools=[investment_decision_agent],
    system_message=(
        "You are the Decision Agent. After reviewing the stock data, news, sentiment, analyst reports, "
        "and expert opinions from the other agents, you provide the final investment decision. In the final decision make a call to either Invest or Not. Also providethe current stock price. "
        "End your response with 'Decision Made' once you finalize the decision."
    )
)

# Stop once "Decision Made" is in the response, or if 15 messages have passed
text_termination = TextMentionTermination("Decision Made")
max_message_termination = MaxMessageTermination(15)
termination = text_termination | max_message_termination

# Round-robin chat among the four agents

investment_team = RoundRobinGroupChat(
    [
        stock_trends_agent_assistant,
        news_agent_assistant,
        sentiment_agent_assistant,
        decision_agent_assistant,
    ],
    termination_condition=termination
)

@cl.on_message
async def run_agent(msg: cl.Message):
    SAVE_DIR = "saved_files"

    # Create the directory if it doesn't exist
    if not os.path.exists(SAVE_DIR):
        os.makedirs(SAVE_DIR)
    file_content = ""
    # Processing the files
    for file in msg.elements:
        print(f"File MIME type: {file.mime}")
        print(uuid)
        if file.mime == "application/pdf":  # PDF files
            print("****************** PDF Found ****************")

            # Define the path where you want to save the file
            unique_id = str(uuid.uuid4())
            saved_file_path = os.path.join(SAVE_DIR, f"{unique_id}_{file.name}")
            
            # Save the file to the local directory
            shutil.copy(file.path, saved_file_path)  # Use shutil to copy the file to the destination
            
            # Now you can open the saved PDF and extract its content
            with fitz.open(saved_file_path) as pdf:
                text = "\n".join([page.get_text("text") for page in pdf])  # Extract text from all pages
                file_content += f"\n\nFile: {file.name}\n{text}"

            # Respond with the location of the saved file
            await cl.Message(content=f"File saved at: {saved_file_path}").send()


    # Append file contents to the user message


    # if not stock_name.strip():
    #     await cl.Message(content="Please provide a valid stock name or file content.").send()
    #     return

    # await cl.Message(content=f"🔍 Analyzing stock trends for **{stock_name}**...").send()

    # print(f"Received stock name and file content: {stock_name}")  # Debugging
    stock_name = msg.content
    if file_content:
        stock_name += file_content
    try:
        print("Getting into Try blocks")
        async for msg in investment_team.run_stream(
            task=f"{stock_name}"
        ):
            if hasattr(msg, "type") and msg.type == "TextMessage":
                await cl.Message(content=msg.content).send()
            else:
                print("Skipping non-text message:", msg)  # Debugging

    except Exception as e:
        await cl.Message(content="⚠️ An error occurred while processing your request.").send()
        print(f"Error: {e}")  # Debugging