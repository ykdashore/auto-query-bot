import logging
import re
from typing import TypedDict, Optional

from dotenv import load_dotenv
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from langchain.schema import BaseOutputParser, AIMessage
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
from src.logger import setup_logger  
from src.get_models import LLMLoader
from src.postgres_manager import SchemaLoader, get_posrtgres_uri

# Load environment variables
load_dotenv('./.env_vars')

logger = setup_logger()

class SQLQAState(TypedDict):
    question: Optional[str]
    sql_query: Optional[str]
    answer: Optional[str]
    chat_history: Optional[str]
    results: Optional[str]

class SQLQueryParser(BaseOutputParser):
    def parse(self, text: str) -> str:
        # Very basic, improve as needed
        if isinstance(text, AIMessage):  # Check if it's an AIMessage
            text = text.content
        match = re.search(r"```sql(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
    
    
class SQLChatBot:
    def __init__(self):
        try:
            logger.info("Initializing chatbot components...")
            self.db_manager = SchemaLoader()
            self.schema_definition = self.db_manager.load_schema_definitions(schemas=["location_management"])
            self.llm = LLMLoader(model_provider='google-gemini').get_model()
            self.memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
            self.sql_prompt = PromptTemplate.from_template(self._sql_prompt_template())
            self.answer_prompt = PromptTemplate.from_template(self._answer_prompt_template())
            self.graph = self._build_graph()
            self.compiled_graph = self.graph.compile()
            logger.info("Chatbot initialized successfully.")
        except Exception as e:
            logger.exception("Failed to initialize SQLChatBot: %s", e)
            raise

    def _sql_prompt_template(self):
        return """
        You are a Postgres SQL expert. Generate **only one SQL query** for the user's question. Return only a syntactically correct SQL query, NO MARKDOWN FORMATTING, No EXPLANATIONS.
        Use the database schema:
        {schema}

        Conversation History:
        {chat_history}

        Question:
        {question}

        Respond ONLY with the SQL query enclosed in 
        sql
        blocks.
        """

    def _answer_prompt_template(self):
        return """
        You have executed the following SQL query:

        SQL Query:
        {sql_query}
        Query Output:
        {results}

        Based on the results (fetched by the user), answer the original question:
        {question}

        If necessary, use the previous chat history:
        {chat_history}

        Answer:
        """

    def _build_graph(self):
        graph = StateGraph(SQLQAState)

        graph.add_node('generate_sql', self.generate_sql)
        graph.add_node('execute_sql', self.execute_sql)
        graph.add_node('generate_answer', self.generate_answer)

        graph.set_entry_point('generate_sql')
        graph.add_edge('generate_sql', 'execute_sql')
        graph.add_edge('execute_sql', 'generate_answer')
        graph.add_edge('generate_answer', END)

        return graph

    def generate_sql(self, state: SQLQAState):
        try:
            formatted_prompt = self.sql_prompt.format_prompt(
                schema=self.schema_definition,
                chat_history=state.get('chat_history', ""),
                question=state['question'],
            )
            logger.info("Generating SQL query...")
            sql_text = self.llm.invoke(formatted_prompt.to_string())
            parser = SQLQueryParser()
            parsed_sql = parser.parse(sql_text)
            logger.info(f"SQL query generated successfully.{parsed_sql}")
            return {"sql_query": parsed_sql}
        except Exception as e:
            logger.exception("Failed to generate SQL query: %s", e)
            raise

    def execute_sql(self, state: SQLQAState):
        try:
            db = SQLDatabase.from_uri(get_posrtgres_uri(), schema="location_management")
            execute_query_tool = QuerySQLDatabaseTool(db=db)
            logger.info("Executing SQL query...")
            results = execute_query_tool.invoke(state['sql_query'])
            logger.info(f"SQL query executed successfully.{results}")
            return {"results": results}
        except Exception as e:
            logger.exception("Failed to execute SQL query: %s", e)
            raise

    def generate_answer(self, state: SQLQAState):
        try:
            formatted_prompt = self.answer_prompt.format_prompt(
                sql_query=state['sql_query'],
                chat_history=state.get('chat_history', ""),
                question=state['question'],
                results=state['results']
            )
            logger.info("Generating final answer...")
            final_answer = self.llm.invoke(formatted_prompt)
            logger.info("Final answer generated successfully.")
            return {"answer": final_answer}
        except Exception as e:
            logger.exception("Failed to generate final answer: %s", e)
            raise

    def chat(self):
        chat_memory = ''
        logger.info("Starting chat session. Type 'exit' or 'quit' to end.")
        try:
            while True:
                user_query = input("\nUser: ")
                if user_query.lower() in ['exit', 'quit']:
                    logger.info("Chat session ended by user.")
                    break

                inputs = {
                    'question': user_query,
                    'chat_history': chat_memory
                }

                result = self.compiled_graph.invoke(inputs)

                print(f"\nAssistant: {result['answer'].content}")

                chat_memory += f"\nUser: {user_query}\nAssistant: {result['answer']}"
        except Exception as e:
            logger.exception("An error occurred during the chat session: %s", e)
            raise

if __name__ == "__main__":
    try:
        bot = SQLChatBot()
        bot.chat()
    except Exception as main_e:
        logger.critical("Unhandled exception occurred in the main application: %s", main_e)
