"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import { publicEnv } from "@/lib/env";

const VAPID_PUBLIC_KEY = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY ?? "";

function urlBase64ToUint8Array(base64String: string) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const output = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i++) {
    output[i] = raw.charCodeAt(i);
  }
  return output;
}

export const PushNotificationToggle = () => {
  const { session } = useAuth();
  const [supported, setSupported] = useState(true);
  const [subscribed, setSubscribed] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkSubscription = useCallback(async () => {
    if (!("serviceWorker" in navigator && "PushManager" in window)) {
      setSupported(false);
      setLoading(false);
      return;
    }

    try {
      const registration = await navigator.serviceWorker.ready;
      const sub = await registration.pushManager.getSubscription();
      setSubscribed(!!sub);
    } catch {
      setSubscribed(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void checkSubscription();
  }, [checkSubscription]);

  if (!supported) {
    return (
      <div className="push-unsupported">
        Push notifications are not supported in this browser.
      </div>
    );
  }

  const handleToggle = async () => {
    if (loading) return;
    setLoading(true);

    try {
      if (subscribed) {
        const registration = await navigator.serviceWorker.ready;
        const sub = await registration.pushManager.getSubscription();
        if (sub) {
          const endpoint = sub.endpoint;
          await sub.unsubscribe();
          if (session?.access_token) {
            await beyulApiFetch("/api/v1/push/unsubscribe", {
              method: "POST",
              accessToken: session.access_token,
              json: { endpoint },
            });
          }
        }
        setSubscribed(false);
      } else {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          setLoading(false);
          return;
        }

        const registration = await navigator.serviceWorker.register("/sw.js");
        await navigator.serviceWorker.ready;

        const sub = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
        });

        const subJson = sub.toJSON();
        if (session?.access_token && subJson.keys) {
          await beyulApiFetch("/api/v1/push/subscribe", {
            method: "POST",
            accessToken: session.access_token,
            json: {
              endpoint: sub.endpoint,
              p256dh: subJson.keys.p256dh,
              auth: subJson.keys.auth,
            },
          });
        }
        setSubscribed(true);
      }
    } catch {
      /* silent */
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="push-toggle">
      <div className="push-info">
        <span className="push-title">Push Notifications</span>
        <span className="push-desc">
          {subscribed
            ? "You're receiving push notifications."
            : "Get notified about market activity and trades."}
        </span>
      </div>
      <label className="push-switch">
        <input
          type="checkbox"
          checked={subscribed}
          disabled={loading}
          onChange={handleToggle}
        />
        <span className="push-slider" />
      </label>
    </div>
  );
};
