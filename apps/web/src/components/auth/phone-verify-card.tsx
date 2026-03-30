"use client";

import { useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/components/auth/auth-provider";
import { AuthFeedback } from "@/components/auth/auth-feedback";
import { useAuthAction } from "@/components/auth/use-auth-action";
import { normalizePhoneNumber } from "@/lib/auth/phone";

export const PhoneVerifyCard = () => {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { sendPhoneOtp, verifyPhoneOtp } = useAuth();
  const [token, setToken] = useState("");
  const phoneFromQuery = searchParams.get("phone") ?? "";
  const normalizedPhone = useMemo(() => {
    try {
      return phoneFromQuery ? normalizePhoneNumber(phoneFromQuery) : "";
    } catch {
      return "";
    }
  }, [phoneFromQuery]);

  const { errorMessage, isSubmitting, runAction, statusMessage, setStatusMessage } = useAuthAction(
    "Enter the OTP code sent to your phone to complete sign-in."
  );

  return (
    <section className="auth-section">
      <h2>Verify phone OTP</h2>
      <p>
        Complete the passwordless phone flow by entering the SMS code. This works with Supabase test phone numbers
        now and real SMS providers later.
      </p>

      <div className="field">
        <label htmlFor="verify-phone-number">Phone number</label>
        <input id="verify-phone-number" disabled value={normalizedPhone || "Missing phone number"} />
      </div>

      <form
        className="auth-form"
        onSubmit={(event) => {
          event.preventDefault();
          void runAction("Verifying phone OTP...", async () => {
            if (!normalizedPhone) {
              throw new Error("A valid phone number is required. Start from the passwordless route.");
            }

            await verifyPhoneOtp(normalizedPhone, token);
            setStatusMessage("Phone OTP verified. Redirecting to your account.");
            router.push("/auth/account");
          });
        }}
      >
        <div className="field">
          <label htmlFor="verify-phone-token">OTP code</label>
          <input
            id="verify-phone-token"
            autoComplete="one-time-code"
            inputMode="numeric"
            placeholder="123456"
            value={token}
            onChange={(event) => setToken(event.target.value)}
          />
        </div>

        <div className="button-row">
          <button className="button-primary" disabled={isSubmitting || !normalizedPhone} type="submit">
            Verify OTP
          </button>
          <button
            className="button-secondary"
            disabled={isSubmitting || !normalizedPhone}
            type="button"
            onClick={() =>
              void runAction("Sending a new phone OTP...", async () => {
                await sendPhoneOtp(normalizedPhone);
                setStatusMessage("A new OTP has been sent.");
              })
            }
          >
            Resend OTP
          </button>
        </div>
      </form>

      <AuthFeedback errorMessage={errorMessage} statusMessage={statusMessage} />
    </section>
  );
};
