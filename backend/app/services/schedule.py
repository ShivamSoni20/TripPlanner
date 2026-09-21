from app.models.domain import ItineraryItem


def validate_schedule(items: list[ItineraryItem]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    ordered = sorted(items, key=lambda item: item.start_at)
    for index, item in enumerate(ordered):
        if item.id in ids:
            errors.append(f"duplicate itinerary id: {item.id}")
        ids.add(item.id)
        if index == 0:
            continue
        previous = ordered[index - 1]
        earliest_start = previous.end_at.timestamp() + item.travel_from_previous_minutes * 60
        if item.start_at.timestamp() < earliest_start:
            errors.append(f"{item.id} starts before required travel completes")
    return errors
