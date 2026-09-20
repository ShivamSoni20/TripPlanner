# TripPilot

## AI Travel Operating System

### Product statement

> **Tell TripPilot where you want to go. It finds the best travel options, builds a budget-aware itinerary, recommends the best places that fit into your available time, provides real booking links, remembers your selections, monitors relevant trip conditions, and re-plans the trip when reality changes.**

TripPilot is not a booking agent.

It does **not**:

- purchase flights;
- book hotels;
- charge cards;
- store payment credentials;
- autonomously spend money.

Instead:

```text
User goal
   ↓
Understand constraints
   ↓
Search live travel options
   ↓
Find best places to visit
   ↓
Optimize around available time
   ↓
Build itinerary
   ↓
Validate budget + routes + opening hours
   ↓
Provide external booking links
   ↓
User books independently
   ↓
TripPilot stores selections
   ↓
Monitor trip
   ↓
Detect disruption / free-time opportunity
   ↓
Re-plan or recommend nearby places

```

---

# 1. Product thesis

Most travel apps solve one part of the problem:

```text
Flights
Hotels
Maps
Weather
Attractions
Reviews
Itinerary

```

The traveller still has to combine everything.

TripPilot treats travel as a continuously changing constrained planning problem.

It answers four questions:

### Before the trip

> What should I book?

### During planning

> What should I do each day?

### During free time

> I have 2 hours here. What's actually worth visiting nearby?

### During disruption

> My flight is late. What parts of my trip should change?

This is the central product concept.

---

# 2. Core differentiator

Do not market this as:

> AI itinerary generator.

Use:

> **A stateful AI travel operating system that continuously optimizes what to do next based on time, location, budget, preferences, and changing conditions.**

The important difference is:

```text
NORMAL AI TRAVEL PLANNER

prompt
 ↓
itinerary
 ↓
done

```

versus:

```text
TRIPPILOT

goal
 ↓
plan
 ↓
travel
 ↓
observe current state
 ↓
find opportunity/problem
 ↓
recommend/re-plan
 ↓
update trip
 ↓
continue

```

---

# 3. New flagship feature

# Smart Free-Time Explorer

The user can ask:

> I have 3 hours free before dinner. What can I visit?

Or TripPilot can detect the gap automatically.

Example:

```text
CURRENT STATE

📍 Candolim, Goa
🕐 Current time: 2:15 PM
🍽 Dinner: 7:30 PM
📍 Dinner location: Panjim

Free window:
2:15 PM → 7:30 PM

```

TripPilot considers:

```text
current location
available time
next scheduled location
travel time
traffic
opening hours
weather
user interests
estimated visit duration
budget
already visited locations
existing itinerary

```

Then returns:

```text
You have enough time for one major stop
or two nearby short stops.

BEST OPTION

🏰 Fort Aguada

Travel there       18 min
Suggested visit    75 min
Travel onward      32 min
Buffer              30 min

Total required     2h 35m

Why this fits:
✓ history matches your interests
✓ highly rated attraction
✓ currently open
✓ low route detour
✓ weather is suitable

[Add to Trip]
[Open in Maps]

```

Alternative:

```text
OPTION 2

🌊 Sinquerim Beach

Travel             12 min
Suggested visit    60 min
Travel onward      29 min

Total               1h 41m

Better if you want a relaxed afternoon.

```

This feature should become one of the strongest portfolio demonstrations.

---

# 4. Why this needs an agent

A normal recommendation system can answer:

> What attractions are near me?

But TripPilot needs to solve:

> Which attraction is worth visiting given everything happening in my trip?

For example:

```text
Candidate A
Rating: 4.8
Distance: 3 km

Candidate B
Rating: 4.6
Distance: 1 km

```

Candidate A isn't automatically better.

It might:

- close in 45 minutes;
- require 40 minutes of traffic;
- be outdoors during rain;
- take too long;
- make the user late for dinner;
- duplicate something they're visiting tomorrow.

The agent therefore combines:

```text
semantic preferences
+
structured live data
+
deterministic constraints

```

---

# 5. Important architecture principle

Do **not** let the LLM determine whether a location fits the schedule.

Use deterministic validation.

Architecture:

```text
LLM
 ↓
"These places look relevant"

Places API
 ↓
"What places actually exist?"

Routes API
 ↓
"How long does travel actually take?"

Opening-hours data
 ↓
"Will it actually be open?"

Weather API
 ↓
"Does the activity make sense?"

Deterministic feasibility engine
 ↓
"Can it physically fit?"

Agent
 ↓
"Which feasible option best matches the traveller?"

```

This separation is important.

---

# 6. Free-time detection

TripPilot should automatically find gaps in the itinerary.

Example:

```text
DAY 2

09:00 Breakfast

10:30 Water Sports
12:30 Ends

--------------------
FREE
12:30–17:30
--------------------

18:00 Sunset Cruise

```

The system detects:

```text
available window = 5 hours

```

Then subtracts:

```text
travel to candidate
+
visit duration
+
travel to next event
+
safety buffer

```

---

# 7. Feasibility equation

For a place to qualify:

```text
travel_to_place
+
visit_duration
+
travel_to_next_event
+
buffer

<=

available_time

```

Example:

```text
Available:
180 minutes

Travel to attraction:
20 min

Recommended visit:
70 min

Travel to dinner:
35 min

Buffer:
20 min

Total:
145 min

145 <= 180

FEASIBLE ✓

```

Another candidate:

```text
Travel:
40

Visit:
100

Travel onward:
35

Buffer:
20

Total:
195

195 > 180

REJECTED ✗

```

The LLM should never override this constraint.

---

# 8. Place discovery

Use:

### Google Places API

Nearby Search supports geographic restrictions and place-type filtering, and results can be ranked by popularity or distance.

Candidate categories might include:

```text
tourist_attraction
museum
art_gallery
park
historical_landmark
beach
shopping
restaurant
cafe
nightlife

```

The category set should depend on user preferences.

Example:

```text
User interests:

history
architecture
food

Search:

historical landmarks
museums
local restaurants
markets

```

Not every possible category.

---

# 9. Nearby candidate retrieval

Tool:

```python
search_nearby_places(
    latitude,
    longitude,
    interests,
    radius,
    max_results
)

```

Normalized result:

```python
class PlaceCandidate(BaseModel):

    place_id: str

    name: str

    category: str

    latitude: float
    longitude: float

    rating: float | None
    rating_count: int | None

    price_level: str | None

    opening_hours: dict | None

    maps_url: str | None

    website_url: str | None

```

Google Places supports filtering/refining place discovery using categories and can return attributes such as ratings, price information, and opening information depending on the endpoint/fields requested.

---

# 10. Route calculation

Use:

### Google Routes API

For:

```text
current position → candidate

candidate → next scheduled activity

```

For multiple candidate places use:

### Compute Route Matrix

Google's Routes API can calculate travel duration and distance across multiple origin/destination combinations, including traffic-aware routing where applicable.

This is ideal for comparing:

```text
Candidate A → Dinner
Candidate B → Dinner
Candidate C → Dinner
Candidate D → Dinner

```

without relying on the LLM.

---

# 11. Candidate filtering pipeline

Start with approximately:

```text
10–20 candidate places

```

Then:

```text
Nearby Search
      ↓
15 candidates
      ↓
Opening-hours filter
      ↓
11 candidates
      ↓
Route feasibility
      ↓
7 candidates
      ↓
Weather compatibility
      ↓
5 candidates
      ↓
Preference scoring
      ↓
Top 3

```

Do not give 20 recommendations to the user.

Usually return:

```text
Best choice

Alternative

Quick option

```

---

# 12. Location recommendation scoring

After hard constraints eliminate impossible options, score the remaining candidates.

Example:

```text
PLACE SCORE

30% preference match

20% place quality

20% route efficiency

10% weather suitability

10% trip diversity

10% cost compatibility

```

Then penalties:

```text
large detour
closing soon
high schedule risk
similar place already visited
requires excessive travel

```

Do not over-optimize this formula in MVP.

It only needs to be transparent and measurable.

---

# 13. Preference matching

This is where the LLM can help.

Example user profile:

```text
likes:
beaches
history
local food

dislikes:
shopping malls
crowds

travel style:
relaxed

```

Candidates:

```text
Fort Aguada
Calangute Mall
Sinquerim Beach
Local Food Market

```

The LLM can determine semantic preference relevance.

But it cannot bypass:

```text
opening hours
travel time
budget
schedule constraints

```

---

# 14. Avoid duplicate experiences

TripPilot should consider:

```text
places already visited

places already scheduled

similar experiences scheduled later

```

Example:

If Day 3 already contains:

```text
Baga Beach
Anjuna Beach

```

then free time on Day 2 might favor:

```text
Fort Aguada

```

rather than adding a third beach.

This makes the itinerary feel intelligent.

---

# 15. Weather-aware discovery

Example:

```text
3-hour free window

Candidates:

Beach
Museum
Market
Fort

```

Weather:

```text
Heavy rain expected

```

Result:

```text
Beach    ↓
Fort     ↓

Museum   ↑
Market   ↑

```

The weather API provides factual conditions.

The agent interprets their implications.

---

# 16. Opening-hours awareness

TripPilot should never recommend:

> Visit museum at 5:30 PM.

when it closes at 5 PM.

Opening-hour data should therefore be checked before recommendation.

Places API exposes opening-hours related fields in its current API.

If opening data is uncertain:

```text
Opening hours couldn't be verified.

[Verify on Google Maps]

```

Do not hallucinate.

---

# 17. Three location-discovery modes

## Mode A — Itinerary optimization

During initial planning:

> What are the best attractions that fit each day?

---

## Mode B — Free-time discovery

During the trip:

> I have 2 hours. Where can I go?

---

## Mode C — Disruption recovery

Something changed:

```text
activity cancelled
flight delayed
rain begins
museum closed

```

TripPilot finds a replacement.

Example:

```text
Water sports cancelled.

You now have:
11:00–14:30 available.

Best replacement:

Museum of Goa
✓ indoors
✓ 21 min away
✓ open
✓ fits before your 3 PM activity

```

This connects the new feature directly to the existing re-planning system.

---

# 18. Updated overall agent workflow

```text
START
 │
 ▼
Understand Trip Request
 │
 ▼
Extract Constraints
 │
 ▼
Search Flights
 │
 ├───────────────┐
 ▼               ▼
Hotels         Places
 │               │
 └───────┬───────┘
         ▼
      Weather
         │
         ▼
Candidate Attractions
         │
         ▼
Route Matrix
         │
         ▼
Time Feasibility Engine
         │
         ▼
Preference Ranking
         │
         ▼
Build Itinerary
         │
         ▼
Budget Validation
         │
         ▼
Schedule Validation
         │
         ▼
Final Trip

```

---

# 19. Updated trip state

```python
class TripState(TypedDict):

    trip_id: str

    constraints: TripConstraints

    flights: list[FlightOption]

    hotels: list[HotelOption]

    place_candidates: list[PlaceCandidate]

    itinerary: list[ItineraryItem]

    selected_flight: str | None
    selected_hotel: str | None

    remaining_budget: float

    visited_places: list[str]

    user_location: GeoPoint | None

    free_time_windows: list[TimeWindow]

    trip_events: list[TripEvent]

    recommendations: list[PlaceRecommendation]

    revision_count: int

```

---

# 20. New TimeWindow model

```python
class TimeWindow(BaseModel):

    start_at: datetime

    end_at: datetime

    origin: GeoPoint

    next_destination: GeoPoint | None

    duration_minutes: int

    travel_mode: str

```

---

# 21. New PlaceRecommendation model

```python
class PlaceRecommendation(BaseModel):

    place_id: str

    name: str

    category: str

    preference_score: float

    travel_to_minutes: int

    recommended_visit_minutes: int

    travel_to_next_minutes: int

    buffer_minutes: int

    required_time_minutes: int

    available_time_minutes: int

    estimated_cost: float | None

    weather_fit: str

    reason: str

    maps_url: str

    feasible: bool

```

---

# 22. User interaction

User can tap:

```text
Explore Nearby

```

TripPilot asks:

```text
How much time do you have?

○ 1 hour
○ 2 hours
○ 3 hours
○ Until my next activity

```

If a next itinerary event exists:

TripPilot already knows the deadline.

---

# 23. Location source

For MVP support:

### Option A

Use current itinerary location.

Example:

```text
Hotel location

```

or last completed activity.

### Option B

Allow:

```text
Use my current location

```

through browser location permission.

Do not require continuous GPS tracking.

That would add privacy and mobile complexity.

---

# 24. Smart recommendation UI

Example:

```text
You have 2h 45m before dinner.

Based on your location and preferences:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⭐ BEST FIT

Fort Aguada

🏰 History
⭐ 4.5

12 min away

Suggested visit:
75 min

Travel to dinner:
28 min

Total:
1h 55m

Leaves:
50 min buffer

Why this works:
• matches your history interest
• minimal route detour
• currently open
• suitable weather

[ Add to Trip ]
[ Open in Maps ]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

QUICK OPTION

Sinquerim Beach

9 min away
60 min visit

[ Add to Trip ]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```

---

# 25. Map visualization

Map should display:

```text
● Current location

● Candidate 1
● Candidate 2
● Candidate 3

★ Next scheduled event

```

And optionally:

```text
Current
   ↓ 12 min
Fort Aguada
   ↓ 28 min
Dinner

```

This makes the reasoning visually obvious.

---

# 26. Updated main planning flow

User:

> Goa for five days from Indore. ₹30k for two people. Beaches, nightlife and history. Relaxed pace.

System:

```text
Parse constraints
       ↓
Search travel
       ↓
Search hotels
       ↓
Find destination attractions
       ↓
Group attractions geographically
       ↓
Calculate travel times
       ↓
Check opening hours
       ↓
Check weather
       ↓
Choose daily activities
       ↓
Optimize free-time windows
       ↓
Validate budget
       ↓
Produce itinerary

```

---

# 27. Geographic clustering

Do not create:

```text
North Goa
↓
South Goa
↓
North Goa

```

on the same day.

Candidate places should be clustered geographically.

For example:

```text
DAY 2 — NORTH GOA

Fort Aguada
↓
Sinquerim
↓
Candolim
↓
Baga

```

Routes data should determine whether this sequence is sensible.

---

# 28. Itinerary optimizer responsibilities

The optimizer must enforce:

```text
No overlapping activities

Enough travel time

Opening-hours compatibility

Arrival before closing

Daily activity limits

Meal/time buffers

Budget limits

User pace preference

Geographic efficiency

```

---

# 29. Relaxed vs packed itinerary

Input:

```text
pace = relaxed

```

Rules:

```text
2–3 major activities/day

30–60 min buffers

less geographic movement

```

Input:

```text
pace = packed

```

Rules:

```text
4–6 activities/day

smaller buffers

more aggressive routing

```

These should be explicit parameters rather than prompt tricks.

---

# 30. Updated system architecture

```text
                           USER
                            │
                            ▼
                     NEXT.JS FRONTEND
                            │
                        REST / SSE
                            │
                            ▼
                         FASTAPI
                            │
                            ▼
                        LANGGRAPH
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
       ▼                    ▼                    ▼
 Constraint Engine      Trip State          Tool Layer
                                                 │
                    ┌────────────────────────────┼─────────────┐
                    │                            │             │
                    ▼                            ▼             ▼
                 Flights                       Hotels        Places
                    │                            │             │
                    ▼                            ▼             ▼
               Flight API                  Hotel API       Google
                                                              │
                                              ┌───────────────┼──────┐
                                              ▼               ▼      ▼
                                           Routes          Weather  Search

                            │
                            ▼
                  TIME FEASIBILITY ENGINE
                            │
                            ▼
                   LOCATION RANKING ENGINE
                            │
                            ▼
                    ITINERARY OPTIMIZER
                            │
                            ▼
                   Supabase / PostgreSQL
                            │
                            ▼
                     Trip Monitoring
                            │
                ┌───────────┴─────────────┐
                ▼                         ▼
          Disruption Event            Free-Time Gap
                │                         │
                ▼                         ▼
             REPLAN                  DISCOVER PLACE

```

---

# 31. Updated tool registry

Core tools:

```text
search_flights()

search_hotels()

search_nearby_places()

get_place_details()

compute_routes()

compute_route_matrix()

get_weather()

get_flight_status()

search_web()

```

Internal deterministic services:

```text
detect_free_time()

calculate_budget()

check_place_feasibility()

rank_places()

validate_itinerary()

detect_schedule_conflicts()

```

---

# 32. Agent vs deterministic code

## Agent

Use AI for:

```text
understanding ambiguous travel goals

semantic preference matching

choosing which information to investigate

comparing trade-offs

explaining recommendations

handling disruption reasoning

deciding which feasible option best matches user intent

```

## Deterministic

Use normal code for:

```text
distance

route duration

time arithmetic

opening-hour checks

budget calculations

availability windows

schedule overlap

hard constraints

ranking arithmetic

URL validation

```

This is a critical architectural distinction.

---

# 33. RAG

## MVP

RAG remains optional.

Do not use it for:

```text
nearby places
distance
ratings
opening hours
current weather
availability
prices

```

Use APIs.

## V1 RAG

Use pgvector for curated:

```text
destination guides

neighborhood descriptions

local cultural context

trip-style guides

seasonal advice

curated travel tips

```

RAG enriches decisions.

It does not determine live reality.

---

# 34. LLM provider

Use:

### OpenRouter

initially.

Architecture:

```text
TripPilot
   ↓
ModelGateway
   ↓
OpenRouter
   ↓
selected model

```

Later benchmark:

```text
OpenRouter model A

OpenRouter model B

Gemini direct

AIML model

```

Do not add multi-model routing to MVP.

---

# 35. LangGraph

### YES

This project now has an even stronger reason for LangGraph.

Stateful transitions include:

```text
planning

location discovery

validation

user selection

trip progression

free-time discovery

monitoring

disruption

re-planning

```

That is an actual graph problem.

---

# 36. Deep Agents

### NO for MVP.

Still unnecessary.

Use Deep Agents only later if you add:

```text
multi-city research

large travel dossiers

specialized research subagents

long-running artifact creation

complex delegation

```

Keep MVP simple.

---

# 37. Booking architecture

TripPilot still never purchases.

Flow:

```text
Recommended Flight
       ↓
[View / Book]
       ↓
Airline / OTA

Recommended Hotel
       ↓
[View / Book]
       ↓
Hotel provider

Recommended Place
       ↓
[Open in Maps]

```

Then:

```text
[I booked this]

```

updates trip state.

---

# 38. User memory

Persist useful preferences:

```text
likes historical places

likes beaches

prefers vegetarian food

avoids very crowded places

prefers relaxed schedules

usually chooses budget hotels

prefers morning flights

```

These influence later ranking.

---

# 39. Monitoring

Monitor only important facts initially:

```text
flight status

weather

```

Then convert changes into:

```text
TripEvent

```

Example:

```json
{
  "type": "FLIGHT_DELAY",
  "delay_minutes": 210
}
```

---

# 40. Re-planning

Original:

```text
09:00 arrival

11:00 hotel

13:00 lunch

15:00 Fort Aguada

18:00 beach

20:30 dinner

```

Flight delayed:

```text
13:00 arrival

```

Agent:

```text
remove impossible lunch

move Fort Aguada → Day 3

preserve beach

preserve dinner

recalculate routes

verify Day 3 still works

```

---

# 41. Free-time recovery

Another situation:

```text
15:00 activity cancelled

Dinner:
19:30

Free:
4 hours

```

Instead of simply deleting the activity:

TripPilot executes:

```text
detect gap
↓
search nearby
↓
route matrix
↓
opening-hours filter
↓
weather filter
↓
preference ranking
↓
recommend replacement

```

This makes disruption recovery considerably more compelling.

---

# 42. Main UI navigation

```text
Trip

├── Overview
├── Itinerary
├── Explore
├── Flights
├── Hotels
├── Map
├── Budget
└── Alerts

```

---

# 43. Explore screen

Dedicated page:

```text
EXPLORE GOA

Where are you now?

📍 Candolim

How much time?

[1 hour]
[2 hours]
[3 hours]
[Until next plan]

What do you feel like?

[Anything]
[Beach]
[Food]
[History]
[Nature]
[Nightlife]

          ↓

Find Places

```

---

# 44. Automatic suggestion

TripPilot can also proactively show:

```text
You have 2h 20m free before your next activity.

I found 3 places nearby that fit your schedule.

[See Suggestions]

```

Do not spam notifications.

Only trigger when:

```text
meaningful free time >= threshold

```

For MVP:

```text
threshold = 90 minutes

```

---

# 45. Evaluation for location optimization

Add specific tests.

## Feasibility accuracy

Of recommended locations:

> How many actually fit the available window?

Target:

```text
100% hard-constraint feasibility

```

because deterministic code handles this.

---

## Route efficiency

Compare:

```text
optimized itinerary travel time

vs.

naive popularity-ranked itinerary

```

Example:

```text
Naive:
210 minutes travelling

TripPilot:
135 minutes travelling

```

Only report measured results.

---

## Preference relevance

Human-label 30 candidate selections.

Compare recommendation to expected interest.

---

## Opening-hour violation rate

Target:

```text
0

```

for places with available opening-hour data.

---

## Schedule conflict rate

Target:

```text
0

```

for deterministic constraints.

---

## Recommendation acceptance

Eventually:

```text
suggestions accepted /
suggestions displayed

```

---

# 46. Updated evaluation suite

Build approximately 30–40 trip scenarios.

Include:

```text
2-hour free window

45-minute free window

attraction closing soon

heavy traffic

rain

next activity far away

multiple nearby attractions

high-rated attraction with huge detour

low-budget traveller

history lover

beach lover

relaxed traveller

already visited attraction

activity cancellation

flight delay

```

---

# 47. Example benchmark

Do not manufacture results.

Eventually publish:

```text
TRIPPILOT EVALUATION

Trip scenarios                     [N]

Valid completed plans              [X]%

Budget violations                  [X]

Schedule conflicts                 [X]

Unsupported place recommendations  [X]

Opening-hour violations            [X]

Free-time feasibility              [X]%

Disruption replan success          [X]%

Mean travel-time reduction         [X]%

Median planning latency            [X]

Average model cost                 $[X]

```

That is excellent portfolio material.

---

# 48. Strongest demo

Use one trip.

## Step 1

Input:

> Plan five days in Goa from Indore for two people under ₹30,000. We like beaches, history and nightlife and prefer relaxed days.

Agent creates trip.

---

## Step 2

Show real options:

```text
Flight

Hotel

Places

Routes

Weather

Budget

```

Open one outbound booking link.

---

## Step 3

Select trip options.

---

## Step 4

Show Day 2.

There is:

```text
2h 45m free

```

Press:

```text
Find something nearby

```

TripPilot:

```text
Current location:
Candolim

Next event:
Dinner 19:30 Panjim

Available:
2h 45m

```

It evaluates:

```text
12 nearby places
↓
7 open
↓
5 fit the route
↓
3 match interests

```

Then recommends:

```text
Fort Aguada

```

with exact timing.

Click:

```text
Add to Trip

```

It appears inside Day 2.

---

# 49. Killer demo extension

Then inject:

```text
Flight delayed 4 hours.

```

TripPilot:

```text
detects affected itinerary
↓
moves Fort Aguada
↓
finds a shorter nearby alternative
↓
recalculates Day 1
↓
shows before / after

```

Now the recruiter has seen the AI:

```text
research

plan

use tools

reason about constraints

change state

react to environment

recover

verify

```

This is substantially stronger than generating travel text.

---

# 50. MVP scope

## MUST BUILD

### Input

```text
origin
destination
dates
travellers
budget
preferences
pace

```

### Agent

```text
constraint extraction

flight search

hotel search

place discovery

route calculation

weather

time feasibility

place ranking

itinerary creation

budget validation

```

### Output

```text
3 flights

3 hotels

day itinerary

map

budget

booking links

best places

free-time suggestions

```

### Agent engineering

```text
persistent trip state

structured tools

LangGraph

basic retry handling

execution trace

20+ evaluation scenarios

```

---

# 51. NICE TO HAVE

After MVP:

```text
flight monitoring

weather monitoring

automatic free-time detection

re-planning

email alerts

persistent user preferences

Mark as Booked

browser geolocation

```

---

# 52. DO NOT BUILD

Avoid:

```text
payments

actual booking

refunds

cancellations

passport storage

visa automation

continuous GPS tracking

group collaboration

voice assistant

native mobile app

restaurant reservation integration

activity purchase integration

complex multi-city trips

Deep Agents

multi-agent architecture

Redis

Celery

Kubernetes

```

Build the intelligent planning loop first.

---

# 53. Minimum stack

## Frontend

```text
Next.js
TypeScript
Tailwind
shadcn/ui
TanStack Query
Google Maps

```

## Backend

```text
Python
FastAPI
Pydantic
httpx

```

## Agent

```text
LangGraph
OpenRouter

```

## Database

```text
Supabase
PostgreSQL

```

## Live data

```text
Flight API

Hotel API

Google Places

Google Routes

Weather API

```

## Observability

```text
LangSmith

```

## Deployment

```text
Vercel
Railway
Supabase

```

---

# 54. Revised build plan

## Days 1–2

Build:

```text
Next.js

FastAPI

Supabase

Trip schema

OpenRouter

TripConstraints extraction

```

Deliverable:

```text
natural language
→
structured trip

```

---

## Days 3–4

Implement normalized:

```text
flight provider

hotel provider

Places API

Weather API

```

Deliverable:

```text
trip
→
real candidate options

```

Use mock flight/hotel providers until production API credentials are available.

---

## Days 5–6

Build:

```text
LangGraph

budget engine

basic itinerary builder

```

Deliverable:

```text
prompt
→
complete trip

```

---

## Days 7–8

Implement:

```text
Routes API

route matrix

free-time detection

place feasibility

```

Deliverable:

```text
"I have 3 hours"
→
best feasible nearby locations

```

---

## Days 9–10

Build UI:

```text
itinerary

map

budget

flight cards

hotel cards

place cards

booking links

Explore screen

```

At this point the project is portfolio-demo ready.

---

## Days 11–12

Add:

```text
20–30 eval scenarios

trace viewer

error handling

fallback provider support

```

---

## Days 13–14

Add the flagship:

```text
mock flight delay
→
impact analysis
→
re-plan
→
free-time replacement

```

Stop there.

Do not keep adding features.

---

# 55. Updated repository

```text
trippilot/
│
├── apps/
│   └── web/
│
├── backend/
│   ├── api/
│   │
│   ├── agent/
│   │   ├── graph.py
│   │   ├── state.py
│   │   └── nodes/
│   │
│   ├── planning/
│   │   ├── budget.py
│   │   ├── scheduler.py
│   │   ├── feasibility.py
│   │   ├── place_ranker.py
│   │   └── free_time.py
│   │
│   ├── tools/
│   │   ├── flights.py
│   │   ├── hotels.py
│   │   ├── places.py
│   │   ├── routes.py
│   │   ├── weather.py
│   │   └── search.py
│   │
│   ├── providers/
│   │
│   └── models/
│
├── evals/
│   ├── trip_scenarios/
│   ├── free_time_scenarios/
│   ├── disruption_scenarios/
│   └── results/
│
├── tests/
│
├── docs/
│   ├── architecture.md
│   ├── agent-loop.md
│   ├── place-optimization.md
│   ├── evaluation.md
│   └── failure-analysis.md
│
├── supabase/
│
└── README.md

```

---

# 56. Updated portfolio pitch

Use:

> **TripPilot is a stateful AI travel operating system that coordinates live flight, hotel, maps, places, routing and weather tools to build budget-constrained trips. Its time-aware recommendation engine discovers worthwhile places that actually fit between existing plans using opening hours, route times, weather, user preferences and schedule constraints. TripPilot links users to external booking providers rather than purchasing on their behalf, then maintains trip state and re-plans affected itinerary segments when conditions change.**

---

# 57. Updated resume bullet

After collecting real measurements:

> **Built TripPilot, a LangGraph-powered travel operating system that orchestrates live travel, places, weather and routing tools to generate budget- and time-constrained itineraries, recommend feasible nearby attractions during free-time windows, and re-plan trips around disruptions; achieved [X]% constraint satisfaction across [N] evaluated scenarios.**

---

# 58. Why the new feature improves the portfolio

Before this feature, the strongest technical story was:

```text
AI searches travel APIs
+
builds itinerary
+
replans

```

Now you also have:

```text
environment state
+
time window
+
geographic search
+
route matrix
+
hard constraint filtering
+
semantic preference ranking
+
dynamic action

```

That is much closer to what an **Applied AI / Agent Engineer** actually builds.

The agent isn't just answering:

> “What should I visit in Goa?”

It is solving:

> **“Given that I'm here, I have 2 hours and 45 minutes, I must be across town by 7:30, rain starts later, I like history, I've already visited two beaches, and I have ₹800 left for activities—what is the highest-value thing I can realistically do now?”**

That is exactly the kind of constrained, tool-grounded decision problem where using an agent makes sense.
