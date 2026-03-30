const getRequiredPublicEnv = (value: string | undefined, key: string): string => {
  if (!value) {
    throw new Error(`Missing required public environment variable: ${key}`);
  }
  return value;
};

const getPublicEnvOrDefault = (value: string | undefined, fallback: string): string => {
  return value || fallback;
};

export const publicEnv = {
  appName: getPublicEnvOrDefault(process.env.NEXT_PUBLIC_APP_NAME, "Satta"),
  siteUrl: getPublicEnvOrDefault(process.env.NEXT_PUBLIC_SITE_URL, "http://localhost:3000"),
  apiBaseUrl: getPublicEnvOrDefault(process.env.NEXT_PUBLIC_API_BASE_URL, "http://localhost:8000"),
  wsBaseUrl: getPublicEnvOrDefault(process.env.NEXT_PUBLIC_WS_BASE_URL, "ws://localhost:9000"),
  supabaseUrl: getRequiredPublicEnv(process.env.NEXT_PUBLIC_SUPABASE_URL, "NEXT_PUBLIC_SUPABASE_URL"),
  supabaseAnonKey: getRequiredPublicEnv(
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    "NEXT_PUBLIC_SUPABASE_ANON_KEY"
  )
};
