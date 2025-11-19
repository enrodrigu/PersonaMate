"""
Refactored core entrypoints and graph construction.

Provides programmatic helpers to build the langgraph StateGraph, run a single chat
exchange, or run a simple interactive loop. Designed to be importable by the
FastAPI backend or other runners.
"""

from dotenv import load_dotenv
load_dotenv()

from typing import Annotated, Tuple, Optional
from typing_extensions import TypedDict
from datetime import datetime
import uuid
from pathlib import Path

from langgraph.graph.message import AnyMessage, add_messages
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph, START
from langgraph.prebuilt import tools_condition

from utils.helper import create_tool_node_with_fallback, _print_event
from tools.personalDataTool import fetch_person_data, update_person_data
from tools.linkingTool import link_elements


# State TypedDict for the graph
class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


class Assistant:
    """Wrapper that invokes a Runnable until it returns a usable response.

    This mirrors the previous behaviour but is easier to test and reuse.
    """

    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state: State, config: RunnableConfig):
        # Keep the original loop behavior: re-run the runnable if content/tool_calls
        # indicate an empty/invalid response.
        while True:
            configuration = config.get("configurable", {})
            state = {**state, **configuration}
            result = self.runnable.invoke(state)
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


def _default_prompt() -> ChatPromptTemplate:
    """Build the primary assistant prompt with a timestamp placeholder."""
    return ChatPromptTemplate.from_messages(
        [
            (
                "system",
                (
                    "You are my personal assistant. Use the provided tools to search for information "
                    "about contacts and the internet. Be persistent when searching; expand queries "
                    "if results are empty. You can ask for more info if needed. Tools available: "
                    "1) Search for a person's data. 2) Update person's data. 3) Create links/likings. "
                    "4) Search the internet. If no tool is needed, respond conversationally.\n"
                    "Current time: {time}."
                ),
            ),
            ("placeholder", "{messages}"),
        ]
    ).partial(time=datetime.now())


def build_graph(thread_id: Optional[str] = None):
    """Construct and compile the StateGraph and return (graph, config).

    The returned `config` contains the `configurable.thread_id` used for
    the MemorySaver checkpointer.
    """

    # Initialize the LLM and tools
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.4)
    tools = [TavilySearchResults(max_results=1), fetch_person_data, update_person_data, link_elements]
    prompt = _default_prompt()
    assistant_runnable = prompt | llm.bind_tools(tools)

    # Build the graph
    builder = StateGraph(State)
    builder.add_node("assistant", Assistant(assistant_runnable))
    builder.add_node("tools", create_tool_node_with_fallback(tools))
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    builder.add_edge("tools", "assistant")

    # Checkpointer / memory
    memory = MemorySaver()
    graph = builder.compile(checkpointer=memory)

    # Provide a minimal config object used when calling graph.stream
    if thread_id is None:
        thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    return graph, config


def chat_once(message: str, graph, config) -> str:
    """Run a single message through the graph and return the assistant text.

    Returns the last non-empty assistant response collected while streaming.
    """
    last_response = ""
    _printed = set()
    events = graph.stream({"messages": ("user", message)}, config, stream_mode="values")
    for event in events:
        response = _print_event(event, _printed)
        if response:
            last_response = response
    return last_response


def interactive_loop(graph, config):
    """Simple CLI interactive loop for local debugging/experimentation."""
    print("Interactive PersonaMate (type 'quit' to exit)")
    _printed = set()
    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break
        events = graph.stream({"messages": ("user", user_input)}, config, stream_mode="values")
        for event in events:
            response = _print_event(event, _printed)
            if response:
                print(f"Assistant: {response}")


if __name__ == "__main__":
    # Simple CLI entrypoint when running the module directly
    g, cfg = build_graph()
    interactive_loop(g, cfg)