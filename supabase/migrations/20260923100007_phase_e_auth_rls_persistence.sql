-- Phase E: Supabase Persistence, Authentication & Ownership RLS Migration

-- 1. Update data_mode check constraint to support 'mixed'
ALTER TABLE public.trips DROP CONSTRAINT IF EXISTS trips_data_mode_check;
ALTER TABLE public.trips ADD CONSTRAINT trips_data_mode_check CHECK (data_mode IN ('demo', 'mixed', 'live'));

-- 2. Modify trips.user_id to be NOT NULL ON DELETE CASCADE
ALTER TABLE public.trips DROP CONSTRAINT IF EXISTS trips_user_id_fkey;
ALTER TABLE public.trips ADD CONSTRAINT trips_user_id_fkey FOREIGN KEY (user_id) REFERENCES auth.users(id) ON DELETE CASCADE;
-- Existing null-owner rows must be inspected and assigned before enabling NOT NULL.
DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.trips WHERE user_id IS NULL) THEN
    RAISE EXCEPTION 'Cannot require trip ownership: null-owner trips exist. Assign owners before this migration.';
  END IF;
END $$;
ALTER TABLE public.trips ALTER COLUMN user_id SET NOT NULL;

-- 3. Add version to trips for optimistic concurrency / stale-state protection
ALTER TABLE public.trips ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1 CHECK (version > 0);

-- 4. Add source to itinerary_items to track origin of items (planned, user_added, replan)
ALTER TABLE public.itinerary_items ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'planned' CHECK (source IN ('planned', 'user_added', 'replan'));

-- 5. Grant required table permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trips TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trip_preferences TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trip_options TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.itinerary_items TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_selections TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trip_events TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trip_alerts TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.agent_runs TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.agent_tool_calls TO authenticated;

-- Ensure anon remains revoked
REVOKE ALL ON public.trips, public.trip_preferences, public.trip_options,
  public.itinerary_items, public.user_selections, public.trip_events,
  public.trip_alerts, public.agent_runs, public.agent_tool_calls FROM anon;

-- Preserve the authoritative planning cost assumptions and provenance across reloads.
ALTER TABLE public.trips ADD COLUMN IF NOT EXISTS plan_metadata jsonb NOT NULL DEFAULT '{}'::jsonb;

-- 6. RLS Policies for trips
DROP POLICY IF EXISTS "Users can select own trips" ON public.trips;
CREATE POLICY "Users can select own trips" ON public.trips FOR SELECT TO authenticated USING ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can insert own trips" ON public.trips;
CREATE POLICY "Users can insert own trips" ON public.trips FOR INSERT TO authenticated WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can update own trips" ON public.trips;
CREATE POLICY "Users can update own trips" ON public.trips FOR UPDATE TO authenticated USING ((select auth.uid()) = user_id) WITH CHECK ((select auth.uid()) = user_id);

DROP POLICY IF EXISTS "Users can delete own trips" ON public.trips;
CREATE POLICY "Users can delete own trips" ON public.trips FOR DELETE TO authenticated USING ((select auth.uid()) = user_id);

-- trip_preferences
DROP POLICY IF EXISTS "Users can select own trip_preferences" ON public.trip_preferences;
CREATE POLICY "Users can select own trip_preferences" ON public.trip_preferences FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_preferences.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can insert own trip_preferences" ON public.trip_preferences;
CREATE POLICY "Users can insert own trip_preferences" ON public.trip_preferences FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_preferences.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can update own trip_preferences" ON public.trip_preferences;
CREATE POLICY "Users can update own trip_preferences" ON public.trip_preferences FOR UPDATE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_preferences.trip_id AND trips.user_id = (select auth.uid()))
) WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_preferences.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can delete own trip_preferences" ON public.trip_preferences;
CREATE POLICY "Users can delete own trip_preferences" ON public.trip_preferences FOR DELETE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_preferences.trip_id AND trips.user_id = (select auth.uid()))
);

-- trip_options
DROP POLICY IF EXISTS "Users can select own trip_options" ON public.trip_options;
CREATE POLICY "Users can select own trip_options" ON public.trip_options FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_options.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can insert own trip_options" ON public.trip_options;
CREATE POLICY "Users can insert own trip_options" ON public.trip_options FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_options.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can update own trip_options" ON public.trip_options;
CREATE POLICY "Users can update own trip_options" ON public.trip_options FOR UPDATE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_options.trip_id AND trips.user_id = (select auth.uid()))
) WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_options.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can delete own trip_options" ON public.trip_options;
CREATE POLICY "Users can delete own trip_options" ON public.trip_options FOR DELETE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_options.trip_id AND trips.user_id = (select auth.uid()))
);

-- itinerary_items
DROP POLICY IF EXISTS "Users can select own itinerary_items" ON public.itinerary_items;
CREATE POLICY "Users can select own itinerary_items" ON public.itinerary_items FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = itinerary_items.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can insert own itinerary_items" ON public.itinerary_items;
CREATE POLICY "Users can insert own itinerary_items" ON public.itinerary_items FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = itinerary_items.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can update own itinerary_items" ON public.itinerary_items;
CREATE POLICY "Users can update own itinerary_items" ON public.itinerary_items FOR UPDATE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = itinerary_items.trip_id AND trips.user_id = (select auth.uid()))
) WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = itinerary_items.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can delete own itinerary_items" ON public.itinerary_items;
CREATE POLICY "Users can delete own itinerary_items" ON public.itinerary_items FOR DELETE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = itinerary_items.trip_id AND trips.user_id = (select auth.uid()))
);

-- user_selections
DROP POLICY IF EXISTS "Users can select own user_selections" ON public.user_selections;
CREATE POLICY "Users can select own user_selections" ON public.user_selections FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = user_selections.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can insert own user_selections" ON public.user_selections;
CREATE POLICY "Users can insert own user_selections" ON public.user_selections FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = user_selections.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can update own user_selections" ON public.user_selections;
CREATE POLICY "Users can update own user_selections" ON public.user_selections FOR UPDATE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = user_selections.trip_id AND trips.user_id = (select auth.uid()))
) WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = user_selections.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can delete own user_selections" ON public.user_selections;
CREATE POLICY "Users can delete own user_selections" ON public.user_selections FOR DELETE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = user_selections.trip_id AND trips.user_id = (select auth.uid()))
);

-- trip_events
DROP POLICY IF EXISTS "Users can select own trip_events" ON public.trip_events;
CREATE POLICY "Users can select own trip_events" ON public.trip_events FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_events.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can insert own trip_events" ON public.trip_events;
CREATE POLICY "Users can insert own trip_events" ON public.trip_events FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_events.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can update own trip_events" ON public.trip_events;
CREATE POLICY "Users can update own trip_events" ON public.trip_events FOR UPDATE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_events.trip_id AND trips.user_id = (select auth.uid()))
) WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_events.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can delete own trip_events" ON public.trip_events;
CREATE POLICY "Users can delete own trip_events" ON public.trip_events FOR DELETE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_events.trip_id AND trips.user_id = (select auth.uid()))
);

-- trip_alerts
DROP POLICY IF EXISTS "Users can select own trip_alerts" ON public.trip_alerts;
CREATE POLICY "Users can select own trip_alerts" ON public.trip_alerts FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_alerts.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can insert own trip_alerts" ON public.trip_alerts;
CREATE POLICY "Users can insert own trip_alerts" ON public.trip_alerts FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_alerts.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can update own trip_alerts" ON public.trip_alerts;
CREATE POLICY "Users can update own trip_alerts" ON public.trip_alerts FOR UPDATE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_alerts.trip_id AND trips.user_id = (select auth.uid()))
) WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_alerts.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can delete own trip_alerts" ON public.trip_alerts;
CREATE POLICY "Users can delete own trip_alerts" ON public.trip_alerts FOR DELETE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = trip_alerts.trip_id AND trips.user_id = (select auth.uid()))
);

-- agent_runs
DROP POLICY IF EXISTS "Users can select own agent_runs" ON public.agent_runs;
CREATE POLICY "Users can select own agent_runs" ON public.agent_runs FOR SELECT TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = agent_runs.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can insert own agent_runs" ON public.agent_runs;
CREATE POLICY "Users can insert own agent_runs" ON public.agent_runs FOR INSERT TO authenticated WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = agent_runs.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can update own agent_runs" ON public.agent_runs;
CREATE POLICY "Users can update own agent_runs" ON public.agent_runs FOR UPDATE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = agent_runs.trip_id AND trips.user_id = (select auth.uid()))
) WITH CHECK (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = agent_runs.trip_id AND trips.user_id = (select auth.uid()))
);

DROP POLICY IF EXISTS "Users can delete own agent_runs" ON public.agent_runs;
CREATE POLICY "Users can delete own agent_runs" ON public.agent_runs FOR DELETE TO authenticated USING (
  EXISTS (SELECT 1 FROM public.trips WHERE trips.id = agent_runs.trip_id AND trips.user_id = (select auth.uid()))
);

-- agent_tool_calls
DROP POLICY IF EXISTS "Users can select own agent_tool_calls" ON public.agent_tool_calls;
CREATE POLICY "Users can select own agent_tool_calls" ON public.agent_tool_calls FOR SELECT TO authenticated USING (
  EXISTS (
    SELECT 1 FROM public.agent_runs
    LEFT JOIN public.trips ON trips.id = agent_runs.trip_id
    WHERE agent_runs.id = agent_tool_calls.run_id
      AND trips.user_id = (select auth.uid())
  )
);

DROP POLICY IF EXISTS "Users can insert own agent_tool_calls" ON public.agent_tool_calls;
CREATE POLICY "Users can insert own agent_tool_calls" ON public.agent_tool_calls FOR INSERT TO authenticated WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.agent_runs
    LEFT JOIN public.trips ON trips.id = agent_runs.trip_id
    WHERE agent_runs.id = agent_tool_calls.run_id
      AND trips.user_id = (select auth.uid())
  )
);

DROP POLICY IF EXISTS "Users can update own agent_tool_calls" ON public.agent_tool_calls;
CREATE POLICY "Users can update own agent_tool_calls" ON public.agent_tool_calls FOR UPDATE TO authenticated USING (
  EXISTS (
    SELECT 1 FROM public.agent_runs
    LEFT JOIN public.trips ON trips.id = agent_runs.trip_id
    WHERE agent_runs.id = agent_tool_calls.run_id
      AND trips.user_id = (select auth.uid())
  )
) WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.agent_runs
    LEFT JOIN public.trips ON trips.id = agent_runs.trip_id
    WHERE agent_runs.id = agent_tool_calls.run_id
      AND trips.user_id = (select auth.uid())
  )
);

DROP POLICY IF EXISTS "Users can delete own agent_tool_calls" ON public.agent_tool_calls;
CREATE POLICY "Users can delete own agent_tool_calls" ON public.agent_tool_calls FOR DELETE TO authenticated USING (
  EXISTS (
    SELECT 1 FROM public.agent_runs
    LEFT JOIN public.trips ON trips.id = agent_runs.trip_id
    WHERE agent_runs.id = agent_tool_calls.run_id
      AND trips.user_id = (select auth.uid())
  )
);

-- Each mutation and its version change commit or roll back as one transaction.
-- SECURITY INVOKER preserves the caller's authenticated RLS context.
CREATE OR REPLACE FUNCTION public.add_user_itinerary_item(
  p_trip_id uuid, p_expected_version integer, p_item jsonb
) RETURNS void LANGUAGE plpgsql SECURITY INVOKER SET search_path = public AS $$
DECLARE v_version integer;
BEGIN
  UPDATE public.trips SET version = version + 1, updated_at = now()
  WHERE id = p_trip_id AND user_id = (SELECT auth.uid()) AND version = p_expected_version
  RETURNING version INTO v_version;
  IF v_version IS NULL THEN RAISE EXCEPTION 'STALE_TRIP_STATE'; END IF;

  INSERT INTO public.itinerary_items
    (id, trip_id, provider_place_id, title, category, start_at, end_at,
     latitude, longitude, cost, currency, travel_from_previous_minutes, source)
  VALUES
    ((p_item->>'id')::uuid, p_trip_id, p_item->>'provider_place_id',
     p_item->>'title', p_item->>'category', (p_item->>'start_at')::timestamptz,
     (p_item->>'end_at')::timestamptz, (p_item->>'latitude')::double precision,
     (p_item->>'longitude')::double precision, (p_item->>'cost')::numeric,
     p_item->>'currency', (p_item->>'travel_from_previous_minutes')::integer,
     'user_added');
END $$;

CREATE OR REPLACE FUNCTION public.remove_user_itinerary_item(
  p_trip_id uuid, p_item_id uuid, p_expected_version integer
) RETURNS void LANGUAGE plpgsql SECURITY INVOKER SET search_path = public AS $$
DECLARE v_version integer;
DECLARE v_deleted uuid;
BEGIN
  UPDATE public.trips SET version = version + 1, updated_at = now()
  WHERE id = p_trip_id AND user_id = (SELECT auth.uid()) AND version = p_expected_version
  RETURNING version INTO v_version;
  IF v_version IS NULL THEN RAISE EXCEPTION 'STALE_TRIP_STATE'; END IF;

  DELETE FROM public.itinerary_items
  WHERE id = p_item_id AND trip_id = p_trip_id AND source = 'user_added'
  RETURNING id INTO v_deleted;
  IF v_deleted IS NULL THEN RAISE EXCEPTION 'ITEM_NOT_REMOVABLE'; END IF;
END $$;

REVOKE ALL ON FUNCTION public.add_user_itinerary_item(uuid, integer, jsonb) FROM PUBLIC, anon;
REVOKE ALL ON FUNCTION public.remove_user_itinerary_item(uuid, uuid, integer) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.add_user_itinerary_item(uuid, integer, jsonb) TO authenticated;
GRANT EXECUTE ON FUNCTION public.remove_user_itinerary_item(uuid, uuid, integer) TO authenticated;
