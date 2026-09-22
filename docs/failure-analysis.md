# Failure analysis

## Null provider ID passed normalization

- **Failure:** the first malformed-record test accepted a Google result with `id: null` and created the internal ID `google:None`.
- **Root cause:** dictionary-key presence was checked, but essential string content was not.
- **Fix:** normalization now rejects empty or non-string place IDs and display names before creating a domain model.
- **Regression:** the Google Places normalization suite covers missing identity, display name, and invalid coordinates.
- **Current status:** fixed.

## Strict TypeScript optional-property regression

- **Failure:** the Phase 2 baseline failed `tsc --noEmit` because an optional property was explicitly assigned `undefined` while `exactOptionalPropertyTypes` was enabled.
- **Root cause:** the API normalizer treated omission and an explicit undefined value as equivalent.
- **Fix:** the normalizer now conditionally spreads the property only when the backend supplied a value.
- **Regression:** Phase 2 verification runs strict TypeScript before each commit.
- **Current status:** fixed.

## Fabricated planning counts

- **Failure:** the prototype displayed fixed counts such as 18 flights regardless of any search.
- **Root cause:** a timer drove presentation-only progress.
- **Fix:** the prompt now calls the backend and the false counts were removed. Demo results carry a visible demo label.
- **Regression:** API tests assert returned collections; the frontend must derive any future count from those collections.

## Disconnected budget totals

- **Failure:** overview and budget screens each contained independent hardcoded totals.
- **Root cause:** the prototype had no shared domain plan.
- **Fix:** the backend performs authoritative arithmetic and both frontend budget surfaces consume the shared `TripPlan` result.
- **Regression:** budget unit tests assert category sum, remaining amount, and overflow status.

## Unsafe outbound URLs

- **Failure:** a future provider adapter could have passed arbitrary schemes or hosts into booking buttons.
- **Root cause:** the prototype had static links and no trust boundary.
- **Fix:** a deterministic validator permits HTTPS and approved provider domains only.
- **Regression:** tests reject non-HTTPS and unapproved domains.

## Impossible schedule transitions

- **Failure:** independently assembled activities could overlap or start before travel completes.
- **Root cause:** UI fixtures had no central schedule validator.
- **Fix:** planning fails validation on overlap or insufficient travel time before a plan is returned.
- **Regression:** schedule tests cover both overlap and travel-buffer violations.

## Supabase CLI produced no project files

- **Failure:** the Windows `npx supabase init` runner exited without diagnostics or generated output.
- **Root cause:** the local npm runner did not execute the downloaded CLI correctly in this environment.
- **Fix:** the standard timestamped migration layout was created directly; the SQL remains compatible with Supabase CLI migration commands.
- **Regression:** CI should add a local database reset check once Docker-backed Supabase is available.

## Unverified route duration entered recommendations

- **Failure:** an absent route matrix leg was previously treated as a 15-minute journey; invalid Google duration text could become zero.
- **Root cause:** fallback values were used where a provider had not supplied a valid duration.
- **Fix:** route normalization rejects invalid duration, and Explorer skips candidates missing either required route leg.
- **Regression:** Google Routes and Explorer feasibility tests cover missing and invalid legs.

## Prototype copy outlived the backend

- **Failure:** Explorer and Route Thread rendered fixed Goa recommendations and travel times even after the backend supplied different plan data.
- **Root cause:** React views retained the original screen fixtures while API calls were added separately.
- **Fix:** views now consume normalized plan and Explorer responses. The decorative map is labeled schematic.
- **Regression:** backend demo smoke checks verify plan, free window, and Explorer output; browser automation is still pending on this host.

## Snake-case payload typed as camel-case data

- **Failure:** flight, hotel, place, and itinerary arrays were typed as frontend domain objects before normalization.
- **Root cause:** the raw API response type reused frontend interfaces.
- **Fix:** raw response shapes are separate, and shared normalizers convert nested fields before state reaches components.
- **Regression:** strict TypeScript and the backend response tests pass; dedicated frontend normalizer tests remain future work.

## Frontend API base URL

- **Failure:** the browser could call the wrong API origin despite a configured environment variable.
- **Root cause:** the client URL builder did not consistently use `VITE_TRIPPILOT_API_URL`.
- **Fix:** planning and Explorer requests use one URL builder.
- **Regression:** local API smoke check and frontend build pass; automated browser E2E remains pending.
