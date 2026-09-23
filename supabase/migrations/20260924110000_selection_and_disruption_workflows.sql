-- Phase F: explicit user selections and durable event/replan workflow metadata.
-- All mutations remain SECURITY INVOKER so the caller's RLS ownership is enforced.

ALTER TABLE public.user_selections
  ADD CONSTRAINT user_selections_type_check
  CHECK (selection_type IN ('selected_flight', 'selected_hotel', 'confirmed_flight', 'confirmed_hotel'));

CREATE UNIQUE INDEX user_selections_trip_type_idx
  ON public.user_selections (trip_id, selection_type);

ALTER TABLE public.trip_events ADD COLUMN IF NOT EXISTS dedupe_key text;
CREATE UNIQUE INDEX trip_events_trip_dedupe_idx
  ON public.trip_events (trip_id, dedupe_key) WHERE dedupe_key IS NOT NULL;

CREATE OR REPLACE FUNCTION public.set_trip_selection(
  p_trip_id uuid,
  p_provider_option_id text,
  p_selection_type text,
  p_expected_version integer,
  p_payload jsonb DEFAULT '{}'::jsonb
) RETURNS void LANGUAGE plpgsql SECURITY INVOKER SET search_path = public AS $$
DECLARE v_option_id uuid;
DECLARE v_expected_type text;
DECLARE v_version integer;
BEGIN
  IF p_selection_type NOT IN ('selected_flight', 'selected_hotel', 'confirmed_flight', 'confirmed_hotel') THEN
    RAISE EXCEPTION 'INVALID_SELECTION_TYPE';
  END IF;
  v_expected_type := CASE WHEN p_selection_type LIKE '%flight' THEN 'flight' ELSE 'hotel' END;
  SELECT id INTO v_option_id FROM public.trip_options
    WHERE trip_id = p_trip_id AND type = v_expected_type AND provider_id = p_provider_option_id;
  IF v_option_id IS NULL THEN RAISE EXCEPTION 'OPTION_NOT_FOUND'; END IF;

  UPDATE public.trips SET version = version + 1, updated_at = now()
    WHERE id = p_trip_id AND user_id = (SELECT auth.uid()) AND version = p_expected_version
    RETURNING version INTO v_version;
  IF v_version IS NULL THEN RAISE EXCEPTION 'STALE_TRIP_STATE'; END IF;

  INSERT INTO public.user_selections (trip_id, option_id, selection_type, payload)
    VALUES (p_trip_id, v_option_id, p_selection_type, COALESCE(p_payload, '{}'::jsonb))
    ON CONFLICT (trip_id, selection_type)
    DO UPDATE SET option_id = EXCLUDED.option_id, payload = EXCLUDED.payload, created_at = now();
END $$;

REVOKE ALL ON FUNCTION public.set_trip_selection(uuid, text, text, integer, jsonb) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.set_trip_selection(uuid, text, text, integer, jsonb) TO authenticated;
