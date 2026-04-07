"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import type { User } from "@supabase/supabase-js";
import { beyulApiFetch } from "@/lib/api/beyul-api";
import type { BackendUser } from "@/lib/api/types";
import { normalizePhoneNumber, normalizePhoneOtpToken } from "@/lib/auth/phone";
import { publicEnv } from "@/lib/env";
import { getSupabaseBrowserClient } from "@/lib/supabase/browser";

type PasswordAuthInput = {
  email: string;
  password: string;
};

type SignUpInput = PasswordAuthInput & {
  username: string;
  displayName: string;
  phone?: string;
};

type AuthSession = {
  access_token: string;
};

type AuthContextValue = {
  session: AuthSession | null;
  user: User | null;
  backendUser: BackendUser | null;
  isReady: boolean;
  signUpWithPassword: (input: SignUpInput) => Promise<void>;
  signInWithPassword: (input: PasswordAuthInput) => Promise<void>;
  sendMagicLink: (email: string) => Promise<void>;
  sendPhoneOtp: (phone: string) => Promise<void>;
  verifyPhoneOtp: (phone: string, token: string) => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

type AuthProviderProps = {
  children: ReactNode;
  initialAccessToken: string | null;
  initialUser: User | null;
};

const toAuthSession = (accessToken: string | null): AuthSession | null =>
  accessToken ? { access_token: accessToken } : null;

export const AuthProvider = ({ children, initialAccessToken, initialUser }: AuthProviderProps) => {
  const [session, setSession] = useState<AuthSession | null>(toAuthSession(initialAccessToken));
  const [user, setUser] = useState<User | null>(initialUser);
  const [backendUser, setBackendUser] = useState<BackendUser | null>(null);
  const [isReady, setIsReady] = useState(false);
  const supabase = getSupabaseBrowserClient();

  useEffect(() => {
    let isMounted = true;

    const syncAuthState = async () => {
      const [{ data: sessionData }, { data: userData }] = await Promise.all([
        supabase.auth.getSession(),
        supabase.auth.getUser()
      ]);

      if (isMounted) {
        setSession(toAuthSession(sessionData.session?.access_token ?? null));
        setUser(userData.user ?? null);
        setIsReady(true);
      }
    };

    void syncAuthState();

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(toAuthSession(nextSession?.access_token ?? null));
      void supabase.auth.getUser().then(({ data }) => {
        if (isMounted) {
          setUser(data.user ?? null);
          setIsReady(true);
        }
      });
    });

    return () => {
      isMounted = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  useEffect(() => {
    let isMounted = true;

    const syncBackendUser = async () => {
      if (!session?.access_token) {
        if (isMounted) {
          setBackendUser(null);
        }
        return;
      }

      try {
        const nextBackendUser = await beyulApiFetch<BackendUser>("/api/v1/auth/me", {
          accessToken: session.access_token
        });
        if (isMounted) {
          setBackendUser(nextBackendUser);
        }
      } catch {
        if (isMounted) {
          setBackendUser(null);
        }
      }
    };

    void syncBackendUser();

    return () => {
      isMounted = false;
    };
  }, [session?.access_token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user,
      backendUser,
      isReady,
      async signUpWithPassword(input) {
        const { error } = await supabase.auth.signUp({
          email: input.email,
          password: input.password,
          options: {
            data: {
              username: input.username,
              display_name: input.displayName,
              phone_e164: input.phone || null
            },
            emailRedirectTo: `${publicEnv.siteUrl}/auth/callback`
          }
        });

        if (error) {
          throw error;
        }
      },
      async signInWithPassword(input) {
        const { error } = await supabase.auth.signInWithPassword(input);
        if (error) {
          throw error;
        }
      },
      async sendMagicLink(email) {
        const { error } = await supabase.auth.signInWithOtp({
          email,
          options: {
            emailRedirectTo: `${publicEnv.siteUrl}/auth/callback`
          }
        });

        if (error) {
          throw error;
        }
      },
      async sendPhoneOtp(phone) {
        const { error } = await supabase.auth.signInWithOtp({
          phone: normalizePhoneNumber(phone)
        });
        if (error) {
          throw error;
        }
      },
      async verifyPhoneOtp(phone, token) {
        const { error } = await supabase.auth.verifyOtp({
          phone: normalizePhoneNumber(phone),
          token: normalizePhoneOtpToken(token),
          type: "sms"
        });
        if (error) {
          throw error;
        }
      },
      async signInWithGoogle() {
        const { error } = await supabase.auth.signInWithOAuth({
          provider: "google",
          options: {
            redirectTo: `${publicEnv.siteUrl}/auth/callback`
          }
        });

        if (error) {
          throw error;
        }
      },
      async signOut() {
        const { error } = await supabase.auth.signOut();
        if (error) {
          throw error;
        }
        setSession(null);
        setUser(null);
        setBackendUser(null);
      },
      async getAccessToken() {
        if (session?.access_token) {
          return session.access_token;
        }
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          throw error;
        }
        return data.session?.access_token ?? null;
      }
    }),
    [backendUser, isReady, session?.access_token, supabase, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }

  return context;
};
