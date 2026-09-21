from app.models.domain import BudgetBreakdown, ItineraryItem


def calculate_budget(
    *,
    budget_limit: int,
    transport: int,
    hotel: int,
    food: int,
    local_transport: int,
    itinerary: list[ItineraryItem],
) -> BudgetBreakdown:
    activities = sum(item.cost.amount for item in itinerary)
    total = transport + hotel + food + local_transport + activities
    return BudgetBreakdown(
        transport=transport,
        hotel=hotel,
        food=food,
        activities=activities,
        local_transport=local_transport,
        total=total,
        remaining=budget_limit - total,
        within_budget=total <= budget_limit,
    )
