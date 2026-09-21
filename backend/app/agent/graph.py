from langgraph.graph import END, START, StateGraph

from app.agent.state import TripAgentState
from app.services.planner import TripPlanner


def build_planning_graph(planner: TripPlanner):
    async def validate_constraints(state: TripAgentState) -> TripAgentState:
        constraints = state.get("constraints")
        if constraints is None:
            return {**state, "errors": ["Trip constraints are missing"]}
        return {**state, "errors": [], "warnings": [], "revision_count": 0}

    async def plan_trip(state: TripAgentState) -> TripAgentState:
        if state.get("errors"):
            return state
        plan = await planner.plan(state["constraints"])
        return {**state, "plan": plan, "warnings": plan.warnings}

    def route_after_validation(state: TripAgentState) -> str:
        return "end" if state.get("errors") else "plan"

    graph = StateGraph(TripAgentState)
    graph.add_node("validate_constraints", validate_constraints)
    graph.add_node("plan_trip", plan_trip)
    graph.add_edge(START, "validate_constraints")
    graph.add_conditional_edges(
        "validate_constraints",
        route_after_validation,
        {"plan": "plan_trip", "end": END},
    )
    graph.add_edge("plan_trip", END)
    return graph.compile()
