const PHONE_E164_PATTERN = /^\+[1-9]\d{7,14}$/;
const OTP_TOKEN_PATTERN = /^\d{4,8}$/;

export const normalizePhoneNumber = (value: string): string => {
  const trimmed = value.trim();
  const compact = trimmed.replace(/[\s()-]/g, "");

  if (!PHONE_E164_PATTERN.test(compact)) {
    throw new Error("Phone number must be in E.164 format, for example +61412345678.");
  }

  return compact;
};

export const normalizePhoneOtpToken = (value: string): string => {
  const compact = value.trim().replace(/\s+/g, "");

  if (!OTP_TOKEN_PATTERN.test(compact)) {
    throw new Error("OTP code must be 4 to 8 digits.");
  }

  return compact;
};
