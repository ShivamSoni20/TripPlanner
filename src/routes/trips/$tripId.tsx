import { createFileRoute } from "@tanstack/react-router";
import { TripPilotApp } from "@/components/trip-pilot";

export const Route = createFileRoute("/trips/$tripId")({
  component: TripRoute,
});

function TripRoute() {
  return <TripPilotApp />;
}
