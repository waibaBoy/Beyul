"use client";

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode
} from "react";
import type { Session, User } from "@supabase/supabase-js";
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

type AuthContextValue = {
  session: Session | null;
  user: User | null;
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
  initialSession: Session | null;
};

export const AuthProvider = ({ children, initialSession }: AuthProviderProps) => {
  const [session, setSession] = useState<Session | null>(initialSession);
  const [user, setUser] = useState<User | null>(initialSession?.user ?? null);
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
        setSession(sessionData.session);
        setUser(userData.user ?? null);
        setIsReady(true);
      }
    };

    void syncAuthState();

    const {
      data: { subscription }
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
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

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      user,
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
      },
      async getAccessToken() {
        const { data, error } = await supabase.auth.getSession();
        if (error) {
          throw error;
        }
        return data.session?.access_token ?? null;
      }
    }),
    [isReady, session, supabase, user]
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
