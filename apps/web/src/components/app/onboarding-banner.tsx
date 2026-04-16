"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/components/auth/auth-provider";

const ONBOARDING_KEY = "satta_onboarding_completed";

const steps = [
  {
    title: "Welcome to Satta!",
    description: "A social prediction market where anyone can create, trade, and settle markets.",
    action: "Get Started",
    href: null,
  },
  {
    title: "Browse Markets",
    description: "Explore live markets or use the search to find topics you care about.",
    action: "View Markets",
    href: "/markets",
  },
  {
    title: "Fund Your Wallet",
    description: "Deposit crypto or fiat to start trading. No fees on deposits!",
    action: "Go to Wallet",
    href: "/wallet",
  },
  {
    title: "Place Your First Trade",
    description: "Pick a market, choose Yes or No, set your quantity, and submit your order.",
    action: "Start Trading",
    href: "/markets",
  },
  {
    title: "Create Your Own Market",
    description: "Got a prediction? Submit a market request and let the community trade on it.",
    action: "Create Market",
    href: "/market-requests",
  },
];

export const OnboardingBanner = () => {
  const { session } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [dismissed, setDismissed] = useState(true);

  useEffect(() => {
    if (!session) return;
    const completed = localStorage.getItem(ONBOARDING_KEY);
    if (!completed) {
      setDismissed(false);
    }
  }, [session]);

  if (dismissed || !session) return null;

  const step = steps[currentStep];
  const isLast = currentStep === steps.length - 1;

  const handleNext = () => {
    if (isLast) {
      localStorage.setItem(ONBOARDING_KEY, "true");
      setDismissed(true);
      return;
    }
    setCurrentStep((s) => s + 1);
  };

  const handleDismiss = () => {
    localStorage.setItem(ONBOARDING_KEY, "true");
    setDismissed(true);
  };

  return (
    <div className="ob-banner">
      <div className="ob-progress">
        {steps.map((_, i) => (
          <div key={i} className={`ob-dot ${i === currentStep ? "is-active" : ""} ${i < currentStep ? "is-done" : ""}`} />
        ))}
      </div>
      <div className="ob-content">
        <h3 className="ob-title">{step.title}</h3>
        <p className="ob-desc">{step.description}</p>
        <div className="ob-actions">
          {step.href ? (
            <a href={step.href} className="ob-action-btn" onClick={handleNext}>
              {step.action}
            </a>
          ) : (
            <button type="button" className="ob-action-btn" onClick={handleNext}>
              {step.action}
            </button>
          )}
          <button type="button" className="ob-dismiss" onClick={handleDismiss}>
            {isLast ? "Done" : "Skip tour"}
          </button>
        </div>
      </div>
    </div>
  );
};
