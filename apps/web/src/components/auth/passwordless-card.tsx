"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { normalizePhoneNumber } from "@/lib/auth/phone";

export const PasswordlessCard = () => {
  const router = useRouter();
  const { sendMagicLink, sendPhoneOtp } = useAuth();
  const [magicEmail, setMagicEmail] = useState("");
  const [phone, setPhone] = useState("");
  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Use passwordless flows for email magic link and phone OTP."
  );

  return (
    <section className="auth-section">
      <h2>Passwordless access</h2>
      <p>Use a magic link or SMS code for a faster sign-in flow without typing a password.</p>

      <div className="auth-form">
        <div className="field">
          <label htmlFor="magic-email">Magic link email</label>
          <input
            id="magic-email"
            autoComplete="email"
            placeholder="you@example.com"
            value={magicEmail}
            onChange={(event) => setMagicEmail(event.target.value)}
          />
        </div>
        <div className="button-row">
          <button
            className="button-secondary"
            disabled={isSubmitting}
            type="button"
            onClick={() =>
              void runAction("Sending magic link...", async () => {
                await sendMagicLink(magicEmail);
                setStatusMessage("Magic link sent.");
              })
            }
          >
            Send magic link
          </button>
        </div>

        <div className="field">
          <label htmlFor="phone-otp">Phone OTP</label>
          <input
            id="phone-otp"
            autoComplete="tel"
            placeholder="+61400000000"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
          />
        </div>
        <div className="button-row">
                <button
                  className="button-secondary"
                  disabled={isSubmitting}
                  type="button"
                  onClick={() =>
                    void runAction("Sending phone OTP...", async () => {
                      const normalizedPhone = normalizePhoneNumber(phone);
                      await sendPhoneOtp(normalizedPhone);
                      setStatusMessage("Phone OTP sent. Redirecting to verification.");
                      router.push(`/auth/phone/verify?phone=${encodeURIComponent(normalizedPhone)}`);
                    })
                  }
                >
                  Send phone OTP
                </button>
        </div>
      </div>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
