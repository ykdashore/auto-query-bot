from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
load_dotenv('E:\\NL2SQL\\.env_vars')
os.environ["GOOGLE_API_KEY"] = os.environ.get('GOOGLE_API_KEY')


class LLMLoader:
    def __init__(self, model_provider):
        self.model_provider = model_provider

    def get_model(self):
        if self.model_provider == "google-gemini":

            llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-001",
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
            )
            return llm
        # TODO
        # wimplement more providers
            
# TODO
class OpenSourceLLMLoader:
    pass