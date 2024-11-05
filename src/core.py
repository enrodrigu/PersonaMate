from dotenv import load_dotenv

load_dotenv()

from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import AnyMessage, add_messages

#Defining the state graph current state

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from personnalDataTool import fetch_person_data
from datetime import datetime

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        while True:
            configuration = config.get("configurable", {})
            state = {**state, **configuration}
            result = self.runnable.invoke(state)
            # If the LLM happens to return an empty response, we will re-prompt it
            # for an actual response.
            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [("user", "Respond with a real output.")]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}


# Initialize the ChatOllama model
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.4
)

primary_assistant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are my personnal assistant"
            " Use the provided tools to search for information about my contacts and search internet to help me. "
            " When searching, be persistent. Expand your query bounds if the first search returns no results. "
            " If a search comes up empty, expand your search before giving up."
            "If no tool is needed, respond conversationally."
            "\nCurrent time: {time}.",
        ),
        ("placeholder", "{messages}"),
    ]
).partial(time=datetime.now())

# Define the tools with required keys
tools = [
    TavilySearchResults(max_results=1),
    fetch_person_data
    ]

assistant_runnable = primary_assistant_prompt | llm.bind_tools(tools)

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import tools_condition
from helper import create_tool_node_with_fallback
from helper import _print_event
import uuid

builder = StateGraph(State)


# Define nodes: these do the work
builder.add_node("assistant", Assistant(assistant_runnable))
builder.add_node("tools", create_tool_node_with_fallback(tools))
# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    tools_condition,
)
builder.add_edge("tools", "assistant")

# The checkpointer lets the graph persist its state
# this is a complete memory for the entire graph.
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

#Printing the graph
from IPython.display import Image, display

try:
    display(Image(graph.get_graph(xray=True).draw_mermaid_png()))
except Exception:
    # This requires some extra dependencies and is optional
    pass

## Using the chatbot


import uuid

# Let's create an example conversation a user might have with the assistant
tutorial_questions = [
    "What is John Doe's favorite food ?",
    "Where can we eat that kind of food in Montréal ?"
]

thread_id = str(uuid.uuid4())

config = {
    "configurable": {
        # Checkpoints are accessed by thread_id
        "thread_id": thread_id,
    }
}


_printed = set()

# makes the chatbot respond to the user's questions
def interact_with_chatbot():
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        events = graph.stream(
            {"messages": ("user", user_input)}, config, stream_mode="values"
        )
        for event in events:
            response = _print_event(event, _printed)
            if response:
                print(f"Assistant: {response}")

if __name__ == "__main__":
    interact_with_chatbot()