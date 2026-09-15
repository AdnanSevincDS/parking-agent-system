from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from parking_agent_system.graph.orchestration import (
    build_pipeline_graph,
    route_after_approval,
    route_after_user,
)

# ===========================
# --- Routing unit tests ---
# ===========================

def test_route_after_user_no_reservation():
    assert route_after_user({"messages": [], "reservation_id": None}) == "end"

def test_route_after_user_with_reservation():
    assert route_after_user({"messages": [], "reservation_id": str(uuid4())}) == "wait_for_admin"

@pytest.mark.parametrize("decision,expected", [
    ("approved", "write_confirmation"),
    ("refused", "end"),
])
def test_route_after_approval(decision, expected):
    assert route_after_approval({"messages": [], "decision": decision}) == expected


# ===========================
# --- Graph building unit tests ---
# ===========================
@pytest.fixture
def interrupted_graph(monkeypatch):
    """Build a MemorySaver graph, run user_node (mocked), leave graph at interrupt."""
    conversation_id = str(uuid4())
    reservation_id = str(uuid4())

    mock_agent = MagicMock()
    mock_agent.run.return_value = ("Reservation created", [])
    
    mock_db = MagicMock()
    mock_db.get_pending_reservations.return_value = [
        {
            "conversation_id": conversation_id,
            "reservation_id": reservation_id,
        }
    ]

    import parking_agent_system.graph.orchestration as orchestration_module

    monkeypatch.setattr(orchestration_module, "ParkingDatabase", lambda: mock_db)
    monkeypatch.setattr(orchestration_module, "agent", mock_agent)

    graph = build_pipeline_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": conversation_id}}

    graph.invoke(
        {"messages": [HumanMessage(content="Make a reservation")],
        "conversation_id": conversation_id,
        },
        config=config,
        )
    return graph, config, reservation_id

def test_graph_interrupts_on_reservation(interrupted_graph):
    graph, config, _ = interrupted_graph
    state = graph.get_state(config)
    assert "wait_for_admin" in state.next

@pytest.mark.parametrize("decision", ["approved", "refused"])
def test_graph_resume_completes(decision, interrupted_graph, monkeypatch):
    graph, config, reservation_id = interrupted_graph

    mock_tool = MagicMock()
    mock_tool.invoke.return_value = f"Reservation {decision}."
    mock_write = MagicMock(return_value="Written to file.")

    import parking_agent_system.graph.orchestration as orchestration_module

    monkeypatch.setattr(orchestration_module, "_call_mcp_write", mock_write)

    if decision == "approved":
        import parking_agent_system.tools.approve_reservation as approve_module
        monkeypatch.setattr(approve_module, "build_approve_reservation_tool", lambda: mock_tool)
    else:
        import parking_agent_system.tools.refuse_reservation as refuse_module
        monkeypatch.setattr(refuse_module, "build_refuse_reservation_tool", lambda: mock_tool)

    graph.invoke(Command(resume=decision), config=config)

    state = graph.get_state(config)

    assert not state.next

    if decision == "approved":
        mock_write.assert_called_once_with(reservation_id)
    else:
        mock_write.assert_not_called()