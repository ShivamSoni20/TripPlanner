import { createFileRoute } from "@tanstack/react-router";
import { TripPilotApp } from "@/components/trip-pilot";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "TripPilot — Your AI Travel Operating System" },
      {
        name: "description",
        content:
          "Plan adaptive trips around your time, budget, location and changing plans with TripPilot.",
      },
      { property: "og:title", content: "TripPilot — Your AI Travel Operating System" },
      {
        property: "og:description",
        content: "Flights, stays, routes and real-world trip changes, organized around you.",
      },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

function Index() {
  return <TripPilotApp />;
}
