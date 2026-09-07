import asyncio
import concurrent.futures
import sqlite3
from uuid import UUID, uuid4
from typing import Annotated,TypedDict, NotRequired

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import BaseMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph.message import add_messages
from langgraph.types import interrupt

from parking_agent_system.config import settings
from parking_agent_system.data_layer.sql_manager import ParkingDatabase

# Load .env variables for LangSmith tracing (LANGSMITH_API_KEY, LANGSMITH_PROJECT)
from dotenv import load_dotenv
load_dotenv()

class PipelineState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    conversation_id: NotRequired[str]
    reservation_id: NotRequired[str | None]
    decision: NotRequired[str | None]
    sources: NotRequired[list]


def user_node(state: PipelineState) -> dict:
    from parking_agent_system.agents.user_agent import ParkingChatAgent
    conversation_id = state.get("conversation_id") or str(uuid4())
    agent = ParkingChatAgent()
    response, sources = agent.run(
        state["messages"][-1].content,
        UUID(conversation_id),
    )

    db = ParkingDatabase()
    reservation_id = None
    for reservation in db.get_pending_reservations():
        if reservation["conversation_id"] == conversation_id:
            reservation_id = reservation["reservation_id"]
            break
    return {
        "messages": [AIMessage(content=response)],
        "sources": sources, 
        "reservation_id": reservation_id,
        "conversation_id": conversation_id
    }

def admin_wait_node(state: PipelineState) -> dict:
    decision = interrupt("Waiting  for admin decision")
    return {
        "decision": decision
    }

def admin_approval_node(state: PipelineState) -> dict:
    reservation_id = state["reservation_id"]
    decision = state["decision"]
    config = {"configurable": {"thread_id": reservation_id}}

    if decision == "approved":
        from parking_agent_system.tools.approve_reservation import build_approve_reservation_tool
        tool = build_approve_reservation_tool()
    else:
        from parking_agent_system.tools.refuse_reservation import build_refuse_reservation_tool
        tool = build_refuse_reservation_tool()
    result = tool.invoke(input={} , config=config)
    return {
        "messages" : [AIMessage(content=result)]
    }

def _call_mcp_write(reservation_id: str) -> str:
    async def _async_call():
        client = MultiServerMCPClient(
            {
                "parking-mcp": {
                    "url": settings.mcp_server_url,
                    "transport": "sse",
                }
            }
        )
        tools = await client.get_tools()
        tool = next(t for t in tools if t.name == "write_confirmed_reservation")
        return await tool.ainvoke({"reservation_id": reservation_id})

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _async_call()).result()


def write_node(state: PipelineState) -> dict:
    try:
        result = _call_mcp_write(state["reservation_id"])
    except Exception as e:
        result = f"MCP Server unavailable: {e}"
    return {
        "messages": [AIMessage(content=str(result))]
    }

def route_after_user(state: PipelineState) -> str:
    return "wait_for_admin" if state.get("reservation_id") else "end"

def route_after_approval(state: PipelineState) -> str:
    return "write_confirmation" if state.get("decision") == "approved" else "end"

def build_pipeline_graph(checkpointer=None):
    graph = StateGraph(PipelineState)
    
    # Graph
    graph = StateGraph(PipelineState)

    # Nodes
    graph.add_node("user_interaction", user_node)
    graph.add_node("wait_for_admin", admin_wait_node)
    graph.add_node("admin_approval", admin_approval_node)
    graph.add_node("write_confirmation", write_node)

    # Edges
    graph.add_edge(START, "user_interaction")
    graph.add_conditional_edges("user_interaction", route_after_user ,{
        "wait_for_admin": "wait_for_admin",
        "end": END
    })
    graph.add_edge("wait_for_admin", "admin_approval")
    graph.add_conditional_edges("admin_approval", route_after_approval, {
        "write_confirmation": "write_confirmation",
        "end": END
    })
    graph.add_edge("write_confirmation", END)

    # Compile  
    return graph.compile(checkpointer=checkpointer)


orchestration_graph = build_pipeline_graph()

# FastAPI — SqliteSaver keeps interrupt state alive between user and admin requests
_conn = sqlite3.connect(str(settings.sqlite_db_path), check_same_thread=False)
api_graph = build_pipeline_graph(checkpointer=SqliteSaver(_conn))