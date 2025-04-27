from dotenv import load_dotenv
load_dotenv('./.env_vars')
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate
from langgraph.graph import StateGraph, END
from langchain.schema import BaseOutputParser
from typing import TypedDict, Optional
from src.get_models import *
from src.postgres_manager import *
from langchain_community.tools.sql_database.tool import QuerySQLDatabaseTool
from langchain_community.utilities import SQLDatabase
from langchain.schema import AIMessage
import re


sql_prompt = PromptTemplate.from_template("""
You are a Postgres SQL expert. Generate **only one SQL query** for the user's question. Return only a syntactically correct SQL query, NO MARKDOWN FORMATTING, No EXPLANATIONS.
Use the database schema:
{schema}

Conversation History:
{chat_history}

Question:
{question}


Respond ONLY with the SQL query enclosed in ```sql``` blocks.
""")

answer_prompt = PromptTemplate.from_template("""
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
""")

db_manager = SchemaLoader()
schema_definition = db_manager.load_schema_definitions(schemas=["location_management"])
llm = LLMLoader(model_provider='google-gemini').get_model()
memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

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
    



def generate_sql(state: SQLQAState):
    formatted_prompt = sql_prompt.format_prompt(
        schema=schema_definition,
        chat_history=state.get('chat_history',""),
        question=state['question'],
    )
    print(schema_definition)
    sql_text = llm.invoke(formatted_prompt.to_string())
    parser = SQLQueryParser()
    parsed_sql = parser.parse(sql_text)
    print(parsed_sql,"---------------")
    return {"sql_query":parsed_sql}

def execute_sql(state: SQLQAState):
    db = SQLDatabase.from_uri(get_posrtgres_uri(), schema="location_management")
    execute_query_tool = QuerySQLDatabaseTool(db=db)
    results = execute_query_tool.invoke(state['sql_query'])
    print(results,"***********")
    return {"results": results}

def generate_answer(state:SQLQAState):
    formatted_prompt = answer_prompt.format_prompt(
        sql_query=state['sql_query'],
        chat_history=state['chat_history'],
        question=state["question"],
        results=state['results']
    )
    final_answer = llm.invoke(formatted_prompt)
    return {"answer":final_answer}

graph = StateGraph(SQLQAState)

# define nodes
graph.add_node('generate_sql', generate_sql)
graph.add_node('execute_sql', execute_sql)
graph.add_node('generate_answer', generate_answer)

# Define Edges
graph.set_entry_point("generate_sql")
graph.add_edge('generate_sql', 'execute_sql')
graph.add_edge('execute_sql', 'generate_answer')
graph.add_edge('generate_answer', END)

compiled_graph = graph.compile()


# chat loop
def chat():
    chat_memory = ''
    while True:
        user_query = input("\nUser: ")
        if user_query.lower() in ['exit', 'quit']:
            break
        inputs = {
            'question':user_query,
            'chat_history': chat_memory
        }

        result = compiled_graph.invoke(inputs)

        print(f"\nAssistant: {result['answer']}")

        chat_memory += f"\nUser: {user_query}\nAssistant: {result['answer']}"

if __name__ == "__main__":
    chat()