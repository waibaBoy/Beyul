import { AppRouteNav } from "@/components/app/app-route-nav";
import { LandingWorkspace } from "@/components/app/landing-workspace";

export default function HomePage() {
  return (
    <div className="app-shell">
      <AppRouteNav />
      <LandingWorkspace />
    </div>
  );
}
