/**
 * Published fee story for marketing / About page. Align matching engine & ledger with these
 * targets before calling them "live" in production.
 */
export const PLATFORM_TAKER_FEE_PERCENT = 2;
export const PLATFORM_MAKER_FEE_PERCENT = 0;

/** Basis points for internal systems (e.g. 200 = 2%). */
export const PLATFORM_TAKER_FEE_BPS = PLATFORM_TAKER_FEE_PERCENT * 100;
export const PLATFORM_MAKER_FEE_BPS = PLATFORM_MAKER_FEE_PERCENT * 100;
