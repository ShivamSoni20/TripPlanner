import asyncio

from app.models.domain import (
    PlaceCandidate,
    PlaceRecommendation,
    TimeWindow,
)
from app.providers.contracts import PlacesProvider, RoutesProvider
from app.services.free_time import get_category_visit_duration, recommend_place


class ExplorerService:
    def __init__(self, places: PlacesProvider, routes: RoutesProvider) -> None:
        self.places = places
        self.routes = routes

    async def explore(
        self,
        *,
        window: TimeWindow,
        interests: list[str],
        excluded_place_ids: list[str] | None = None,
        remaining_budget: int | None = None,
        safety_buffer_minutes: int = 15,
    ) -> list[PlaceRecommendation]:
        excluded = set(excluded_place_ids or [])
        candidates = await self.places.search_nearby(
            location=window.origin,
            interests=interests or ["tourist attractions"],
            radius_meters=10000,
            max_results=12,
        )

        filtered = [
            c for c in candidates if c.place_id not in excluded and c.provider_id not in excluded
        ]
        if not filtered:
            return []

        destinations = [c.location for c in filtered]

        # Batch matrix A: origin -> candidates
        # Batch matrix B: candidates -> next_destination (if present)
        matrix_a_task = self.routes.compute_matrix([window.origin], destinations)
        matrix_b_task = (
            self.routes.compute_matrix(destinations, [window.next_destination])
            if window.next_destination
            else asyncio.sleep(0, result=[])
        )

        matrix_a_entries, matrix_b_entries = await asyncio.gather(matrix_a_task, matrix_b_task)

        # Map travel to candidates
        travel_to_map: dict[int, int] = {}
        for entry in matrix_a_entries:
            if entry.route_exists and entry.duration_minutes is not None:
                travel_to_map[entry.destination_index] = entry.duration_minutes

        # Map travel candidate -> next event
        travel_next_map: dict[int, int] = {}
        if window.next_destination:
            for entry in matrix_b_entries:
                if entry.route_exists and entry.duration_minutes is not None:
                    travel_next_map[entry.origin_index] = entry.duration_minutes

        evaluated: list[tuple[PlaceCandidate, int, int, int, float, list[str]]] = []

        for idx, candidate in enumerate(filtered):
            travel_to = travel_to_map.get(idx)
            travel_next = 0 if not window.next_destination else travel_next_map.get(idx)
            if travel_to is None or travel_next is None:
                continue
            visit = get_category_visit_duration(candidate)

            total_required = travel_to + visit + travel_next + safety_buffer_minutes
            if total_required > window.duration_minutes:
                continue

            # Check budget fit if specified
            if remaining_budget is not None and candidate.price.amount > remaining_budget:
                continue

            # Calculate score
            pref_match = (
                0.35 if any(i.lower() in candidate.interest_tags for i in interests) else 0.15
            )
            rating_score = ((candidate.rating or 4.0) / 5.0) * 0.25
            time_ratio = (travel_to + travel_next) / float(window.duration_minutes)
            efficiency_score = max(0.0, 0.30 * (1.0 - time_ratio))
            open_bonus = 0.10 if (candidate.open_now is True or candidate.opening_hours) else 0.05

            score = min(1.0, round(pref_match + rating_score + efficiency_score + open_bonus, 2))

            reasons: list[str] = []
            if candidate.rating and candidate.rating >= 4.5:
                reasons.append(f"Highly rated ({candidate.rating}★)")
            if any(i.lower() in candidate.interest_tags for i in interests):
                reasons.append("Matches your trip interests")
            reasons.append(f"{travel_to} min travel time")

            evaluated.append((candidate, travel_to, visit, travel_next, score, reasons))

        if not evaluated:
            return []

        # Sort by score descending
        evaluated.sort(key=lambda item: item[4], reverse=True)

        recommendations: list[PlaceRecommendation] = []
        best_fit = evaluated[0]
        recommendations.append(
            recommend_place(
                rank="Best Fit",
                place=best_fit[0],
                window=window,
                travel_to_minutes=best_fit[1],
                travel_to_next_minutes=best_fit[3],
                safety_buffer_minutes=safety_buffer_minutes,
                score=best_fit[4],
                reason=best_fit[5],
            )
        )

        if len(evaluated) > 1:
            alt = evaluated[1]
            recommendations.append(
                recommend_place(
                    rank="Alternative",
                    place=alt[0],
                    window=window,
                    travel_to_minutes=alt[1],
                    travel_to_next_minutes=alt[3],
                    safety_buffer_minutes=safety_buffer_minutes,
                    score=alt[4],
                    reason=alt[5],
                )
            )

        # Quick Option: candidate with lowest total travel time (travel_to + travel_next)
        quick_candidate = min(evaluated, key=lambda item: item[1] + item[3])
        if quick_candidate[0].place_id not in [r.place.place_id for r in recommendations]:
            quick_reasons = list(quick_candidate[5])
            quick_reasons.append("Shortest travel distance")
            recommendations.append(
                recommend_place(
                    rank="Quick Option",
                    place=quick_candidate[0],
                    window=window,
                    travel_to_minutes=quick_candidate[1],
                    travel_to_next_minutes=quick_candidate[3],
                    safety_buffer_minutes=safety_buffer_minutes,
                    score=quick_candidate[4],
                    reason=quick_reasons,
                )
            )

        return recommendations
