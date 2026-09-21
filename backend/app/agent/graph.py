from langgraph.graph import END, START, StateGraph

from app.agent.state import TripAgentState
from app.services.planner import TripPlanner
from app.services.trip_extraction import TripExtractor


def build_planning_graph(planner: TripPlanner, extractor: TripExtractor):
    async def parse_constraints(state: TripAgentState) -> TripAgentState:
        extraction = await extractor.extract(state["prompt"])
        if extraction.status == "needs_input":
            return {
                **state,
                "extraction": extraction,
                "missing": extraction.missing,
                "errors": [],
            }
        return {
            **state,
            "extraction": extraction,
            "constraints": extraction.constraints,
            "missing": [],
        }

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

    def route_after_parsing(state: TripAgentState) -> str:
        return "end" if state.get("missing") else "validate"

    graph = StateGraph(TripAgentState)
    graph.add_node("parse_constraints", parse_constraints)
    graph.add_node("validate_constraints", validate_constraints)
    graph.add_node("plan_trip", plan_trip)
    graph.add_edge(START, "parse_constraints")
    graph.add_conditional_edges(
        "parse_constraints",
        route_after_parsing,
        {"validate": "validate_constraints", "end": END},
    )
    graph.add_conditional_edges(
        "validate_constraints",
        route_after_validation,
        {"plan": "plan_trip", "end": END},
    )
    graph.add_edge("plan_trip", END)
    return graph.compile()
