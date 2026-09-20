# TripPilot responsive application UI

## Goal

Build a polished, interactive front-end prototype of TripPilot as an AI Travel Operating System—not a chatbot. The product will visibly organize one consistent Goa adventure around time, budget, location, preferences, and real-world changes.

## Core demo narrative

Use one shared trip state throughout:

- Indore → Goa, 12–17 November, two travellers
- ₹30,000 budget; beaches, history, nightlife; relaxed pace
- New Trip → Planning → Generated Trip → Free-Time Explorer → Add Fort Aguada → Updated itinerary/map/budget → Simulated flight delay → Re-plan → Accept revised plan

## Application structure

- Replace the placeholder at `/` with the spacious new-trip experience and transition into structured planning.
- Build a persistent generated-trip shell with shareable views for Overview, Itinerary, Explore, Flights, Hotels, Map, Budget, and Alerts.
- Keep the trip’s selected stop, added recommendation, budget, alert, and accepted re-plan state synchronized across all views.
- Desktop uses persistent top navigation and content/map splits; mobile uses Trip, Explore, Map, and Alerts bottom navigation plus compact secondary controls.

## Screens and key interactions

1. **New Trip** — large natural-language field, supplied example, five suggestion chips, coral planning action, and restrained cartographic decoration.
2. **Planning** — sequential high-level agent activities with completion/result states and a route preview; no chat bubbles or chain-of-thought.
3. **Overview** — Goa hero, dates, travellers, ₹28,450 / ₹30,000 meter, weather, current status, next event, saved travel summary, map, and free-time insight.
4. **Itinerary** — functional vertical Route Thread with numbered stops, photos, travel-time connectors, free-time block, synchronized map selection, and visible changes after insertion/re-planning.
5. **Smart Explorer** — exactly three ranked recommendations: Best Fit, Alternative, and Quick Option. Filters, timing constraints, cost, opening/weather status, safety buffer, rationale, and a route-aware map are all visible.
6. **Add to Today** — selecting Fort Aguada transitions its card into the timeline, redraws the Route Thread and map, reduces the free-time window, and confirms the budget remains valid.
7. **Flights** — scan-friendly options with rationale, freshness/stale indicators, partial/failure states, and outbound “View & Book” actions only.
8. **Hotels** — photo-led options with cost, location, amenities, average itinerary travel time, rationale, and outbound booking actions.
9. **Map** — reusable map container with coral numbered pins, hotel/current location/candidates/next event, Route Thread paths, and two-way selection with itinerary cards. Desktop uses a floating list; mobile uses a bottom sheet and map/list toggle.
10. **Budget** — friendly pastel category breakdown, ₹1,550 buffer, and travel-focused TripPilot insight; updates when itinerary state changes.
11. **Alerts** — flight, weather, closure, stale-price, and free-time notices that explain direct itinerary impact.
12. **Disruption and re-plan** — calm peach flight-delay notice, original-versus-updated Day 1 comparison, “Use New Plan” and “Keep Original,” followed by synchronized itinerary, route, map, and budget updates.
13. **System states** — include loading, offline, partial results, unavailable flight search, stale prices, and the important “nothing worthwhile fits safely” recommendation state.

## Reusable component system

Create focused components for:

- AppShell, TripPrompt, AgentProgress, AgentActivity, TripHero
- BudgetMeter, WeatherChip, FilterChip, BookingLinkButton
- FlightCard, HotelCard, PlaceCard, SmartRecommendationCard
- ItineraryTimeline, RouteThread, FreeTimeCard, TripMap
- TripAlert, ReplanComparison, MobileBottomSheet

Use the existing accessible interface primitives and Lucide icons. Keep demo state typed and centralized so route, timeline, map, budget, and alert interactions stay consistent.

## Visual implementation

- Implement “Sunlit Cartography + Soft Bento Travel UI” through semantic theme tokens using the supplied warm background, coral, mint, sky, butter, lavender, peach, text, and border colors.
- Use Plus Jakarta Sans headings and Inter body/interface text, loaded from the document head.
- Use 20–28px rounded cards, thin borders, extremely soft shadows, generous whitespace, destination photography, route lines, playful pins, and restrained journal details.
- Generate a cohesive Goa image set for trip, hotel, itinerary, and recommendation cards; avoid generic or unrelated imagery.
- Make the four-point navigation star TripPilot’s AI mark; use production icons instead of emojis elsewhere.
- Add restrained Motion animations for progress checks, route drawing, card entry, recommendation insertion, selected routes, budget fill, and re-planning, with reduced-motion support.

## Responsive and accessibility quality

- Support mobile through 1440px desktop with stable dimensions for maps, cards, navigation, timelines, and controls.
- Preserve the Route Thread on mobile, use horizontal recommendation swiping, sticky primary actions, compact filters, and map bottom sheets.
- Keep interface text at 14px or larger, meet WCAG AA contrast, provide keyboard-operable interactions, strong focus indicators, useful labels, and no overlapping content.
- Validate the full primary flow and major views at desktop and mobile sizes, including map/card synchronization, state changes, overflow, imagery, and reduced motion.
- Add unique TripPilot metadata to every content route.

## Technical scope

- Front-end prototype using local realistic demo data and in-memory state; no authentication or persistence.
- The map is a purpose-built interactive visual container designed for later Google Maps or Mapbox integration, not a tightly coupled fake provider.
- No live flight, hotel, weather, maps, booking, purchasing, payment, or AI services in this phase.
- External booking/map controls remain clearly outbound and never imply TripPilot completes a purchase.
