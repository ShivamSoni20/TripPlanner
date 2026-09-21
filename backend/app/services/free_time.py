from app.models.domain import PlaceCandidate, PlaceRecommendation, TimeWindow


def is_feasible(
    *,
    window: TimeWindow,
    travel_to_minutes: int,
    visit_duration_minutes: int,
    travel_to_next_minutes: int,
    safety_buffer_minutes: int,
) -> bool:
    required = (
        travel_to_minutes + visit_duration_minutes + travel_to_next_minutes + safety_buffer_minutes
    )
    return required <= window.duration_minutes


def recommend_place(
    *,
    rank: str,
    place: PlaceCandidate,
    window: TimeWindow,
    travel_to_minutes: int,
    travel_to_next_minutes: int,
    safety_buffer_minutes: int,
    score: float,
    reason: list[str],
) -> PlaceRecommendation:
    visit = place.suggested_visit_minutes
    return PlaceRecommendation(
        rank=rank,
        place=place,
        travel_to_minutes=travel_to_minutes,
        visit_duration_minutes=visit,
        travel_to_next_minutes=travel_to_next_minutes,
        safety_buffer_minutes=safety_buffer_minutes,
        score=score,
        reason=reason,
        feasible=is_feasible(
            window=window,
            travel_to_minutes=travel_to_minutes,
            visit_duration_minutes=visit,
            travel_to_next_minutes=travel_to_next_minutes,
            safety_buffer_minutes=safety_buffer_minutes,
        ),
    )
