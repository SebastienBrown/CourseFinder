import os
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

load_dotenv()

llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_CHATOPENAI_ENDPOINT"],
    azure_deployment=os.environ["AZURE_CHATOPENAI_DEPLOYMENT"],
    openai_api_version=os.environ["CHATOPENAI_API_VERSION"],
    openai_api_key=os.environ["AZURE_CHATOPENAI_API_KEY"]
)
