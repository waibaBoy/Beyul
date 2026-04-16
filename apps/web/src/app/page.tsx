import { AppRouteNav } from "@/components/app/app-route-nav";
import { LandingWorkspace } from "@/components/app/landing-workspace";
import { OnboardingBanner } from "@/components/app/onboarding-banner";

export default function HomePage() {
  return (
    <div className="app-shell">
      <AppRouteNav />
      <OnboardingBanner />
      <LandingWorkspace />
    </div>
  );
}
