from datetime import datetime, timedelta

from app.models.domain import ItineraryItem, PlaceCandidate, PlaceRecommendation, TimeWindow


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


def detect_free_windows(
    itinerary: list[ItineraryItem],
    min_duration_minutes: int = 45,
) -> list[TimeWindow]:
    if len(itinerary) < 2:
        return []
    ordered = sorted(itinerary, key=lambda item: item.start_at)
    windows: list[TimeWindow] = []
    for index in range(len(ordered) - 1):
        current_item = ordered[index]
        next_item = ordered[index + 1]
        gap_seconds = (next_item.start_at - current_item.end_at).total_seconds()
        gap_minutes = int(gap_seconds / 60)
        if gap_minutes >= min_duration_minutes:
            windows.append(
                TimeWindow(
                    start_at=current_item.end_at,
                    end_at=next_item.start_at,
                    origin=current_item.location,
                    next_destination=next_item.location,
                    duration_minutes=gap_minutes,
                )
            )
    return windows


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
    visit = get_category_visit_duration(place)
    total_required = travel_to_minutes + visit + travel_to_next_minutes + safety_buffer_minutes
    remaining_buffer = window.duration_minutes - total_required
    feasible = total_required <= window.duration_minutes
    return PlaceRecommendation(
        rank=rank,
        place=place,
        travel_to_minutes=travel_to_minutes,
        visit_duration_minutes=visit,
        travel_to_next_minutes=travel_to_next_minutes,
        safety_buffer_minutes=safety_buffer_minutes,
        total_required_minutes=total_required,
        remaining_buffer_minutes=max(0, remaining_buffer),
        score=score,
        reason=reason,
        feasible=feasible,
    )


def get_category_visit_duration(place: PlaceCandidate) -> int:
    category = (place.category or "").lower()
    types = [t.lower() for t in place.types]
    if "museum" in category or "museum" in types:
        return 90
    if "beach" in category or "beach" in types:
        return 90
    if "historical_landmark" in category or "historical_landmark" in types or "history" in category:
        return 75
    if "park" in category or "park" in types:
        return 60
    if "restaurant" in category or "restaurant" in types:
        return 60
    if "cafe" in category or "cafe" in types:
        return 45
    if "bar" in category or "bar" in types or "night_club" in types:
        return 90
    return place.suggested_visit_minutes or 60


def is_open_for_visit(place: PlaceCandidate, start_at: datetime, duration_minutes: int) -> bool | None:
    """Return whether a known schedule covers the whole proposed visit; None means unknown."""
    hours = place.opening_hours
    if not hours or not hours.periods:
        return None
    end_at = start_at + timedelta(minutes=duration_minutes)
    # Google uses Sunday=0 while Python's weekday uses Monday=0.
    for period in hours.periods:
        open_day = (period.open_day - 1) % 7
        if start_at.weekday() != open_day:
            continue
        open_at = start_at.replace(hour=period.open_hour, minute=period.open_minute, second=0)
        close_day = (period.close_day - 1) % 7 if period.close_day is not None else open_day
        day_delta = (close_day - open_day) % 7
        close_at = open_at.replace(hour=period.close_hour or 0, minute=period.close_minute or 0)
        close_at += timedelta(days=day_delta)
        if period.close_hour is None or period.close_minute is None:
            continue
        if open_at <= start_at and end_at <= close_at:
            return True
    return False
