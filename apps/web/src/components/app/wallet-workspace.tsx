"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { beyulApiFetch } from "@/lib/api/beyul-api";

type Transfer = {
  id: string;
  direction: "deposit" | "withdrawal";
  rail: string;
  asset_code: string;
  amount: number;
  fee_amount: number;
  net_amount: number;
  status: string;
  wallet_address: string | null;
  created_at: string;
  completed_at: string | null;
};

type TransfersResponse = {
  transfers: Transfer[];
  count: number;
};

type Tab = "deposit" | "withdraw";
type Rail = "crypto" | "fiat_bank" | "fiat_card";

const WITHDRAWAL_FEE_RATE = 0.005;
const MIN_WITHDRAWAL = 10;
const MAX_WITHDRAWAL = 50_000;

const fmt = (n: number) => n.toFixed(2);

const railLabel = (rail: Rail) => {
  switch (rail) {
    case "crypto":
      return "Crypto (USDC)";
    case "fiat_bank":
      return "Bank transfer";
    case "fiat_card":
      return "Card";
  }
};

const statusClass = (status: string) => {
  switch (status) {
    case "pending":
      return "wlt-badge wlt-badge-pending";
    case "processing":
      return "wlt-badge wlt-badge-processing";
    case "completed":
      return "wlt-badge wlt-badge-completed";
    case "failed":
      return "wlt-badge wlt-badge-failed";
    case "cancelled":
      return "wlt-badge wlt-badge-cancelled";
    default:
      return "wlt-badge";
  }
};

const formatDate = (iso: string) => {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
};

export const WalletWorkspace = () => {
  const { session, user, isReady, getAccessToken } = useAuth();
  const [tab, setTab] = useState<Tab>("deposit");
  const [amount, setAmount] = useState("");
  const [rail, setRail] = useState<Rail>("crypto");
  const [walletAddress, setWalletAddress] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const fetchHistory = useCallback(async () => {
    const token = await getAccessToken();
    if (!token) return;
    setLoadingHistory(true);
    try {
      const data = await beyulApiFetch<TransfersResponse>("/api/v1/transfers/me", {
        accessToken: token,
      });
      setTransfers(data.transfers);
    } catch {
      // silently fail on history fetch
    } finally {
      setLoadingHistory(false);
    }
  }, [getAccessToken]);

  useEffect(() => {
    if (session?.access_token) {
      void fetchHistory();
    }
  }, [session?.access_token, fetchHistory]);

  if (!isReady) {
    return <div className="wlt-loading">Loading…</div>;
  }

  if (!user) {
    return (
      <div className="wlt-sign-in">
        <Link href="/auth/sign-in">Sign in</Link> to access your wallet.
      </div>
    );
  }

  const parsedAmount = parseFloat(amount) || 0;
  const withdrawalFee = parsedAmount * WITHDRAWAL_FEE_RATE;
  const withdrawalNet = parsedAmount - withdrawalFee;

  const canSubmitDeposit = parsedAmount > 0 && (rail !== "crypto" || walletAddress.trim().length > 0);
  const canSubmitWithdraw =
    parsedAmount >= MIN_WITHDRAWAL &&
    parsedAmount <= MAX_WITHDRAWAL &&
    (rail !== "crypto" || walletAddress.trim().length > 0);

  const handleSubmit = async () => {
    setError(null);
    setSuccess(null);
    setSubmitting(true);

    try {
      const token = await getAccessToken();
      const endpoint =
        tab === "deposit" ? "/api/v1/transfers/deposit" : "/api/v1/transfers/withdrawal";

      await beyulApiFetch(endpoint, {
        method: "POST",
        accessToken: token,
        json: {
          amount: parsedAmount,
          rail,
          asset_code: "USDC",
          wallet_address: rail === "crypto" ? walletAddress.trim() : undefined,
        },
      });

      setSuccess(tab === "deposit" ? "Deposit submitted." : "Withdrawal submitted.");
      setAmount("");
      setWalletAddress("");
      void fetchHistory();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="wlt-shell">
      <div className="wlt-tab-bar">
        <button
          className={`wlt-tab ${tab === "deposit" ? "is-active" : ""}`}
          onClick={() => { setTab("deposit"); setError(null); setSuccess(null); }}
          type="button"
        >
          Deposit
        </button>
        <button
          className={`wlt-tab ${tab === "withdraw" ? "is-active" : ""}`}
          onClick={() => { setTab("withdraw"); setError(null); setSuccess(null); }}
          type="button"
        >
          Withdraw
        </button>
      </div>

      {tab === "deposit" ? (
        <form
          className="wlt-form"
          onSubmit={(e) => { e.preventDefault(); void handleSubmit(); }}
        >
          <div className="wlt-field">
            <label className="wlt-label" htmlFor="dep-amount">Amount (USDC)</label>
            <input
              id="dep-amount"
              className="wlt-input"
              type="number"
              min="0"
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>

          <div className="wlt-field">
            <label className="wlt-label" htmlFor="dep-rail">Payment rail</label>
            <select
              id="dep-rail"
              className="wlt-select"
              value={rail}
              onChange={(e) => setRail(e.target.value as Rail)}
            >
              <option value="crypto">{railLabel("crypto")}</option>
              <option value="fiat_bank">{railLabel("fiat_bank")}</option>
              <option value="fiat_card">{railLabel("fiat_card")}</option>
            </select>
          </div>

          {rail === "crypto" && (
            <div className="wlt-field">
              <label className="wlt-label" htmlFor="dep-wallet">Wallet address</label>
              <input
                id="dep-wallet"
                className="wlt-input"
                type="text"
                placeholder="0x…"
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value)}
              />
            </div>
          )}

          <p className="wlt-note">No fees on deposits.</p>

          {error && <p className="wlt-note" style={{ color: "var(--no)" }}>{error}</p>}
          {success && <p className="wlt-note" style={{ color: "var(--yes)" }}>{success}</p>}

          <button className="wlt-submit" type="submit" disabled={!canSubmitDeposit || submitting}>
            {submitting ? "Submitting…" : "Deposit"}
          </button>
        </form>
      ) : (
        <form
          className="wlt-form"
          onSubmit={(e) => { e.preventDefault(); void handleSubmit(); }}
        >
          <div className="wlt-field">
            <label className="wlt-label" htmlFor="wd-amount">Amount (USDC)</label>
            <input
              id="wd-amount"
              className="wlt-input"
              type="number"
              min={MIN_WITHDRAWAL}
              max={MAX_WITHDRAWAL}
              step="0.01"
              placeholder="0.00"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>

          <div className="wlt-field">
            <label className="wlt-label" htmlFor="wd-rail">Payment rail</label>
            <select
              id="wd-rail"
              className="wlt-select"
              value={rail}
              onChange={(e) => setRail(e.target.value as Rail)}
            >
              <option value="crypto">{railLabel("crypto")}</option>
              <option value="fiat_bank">{railLabel("fiat_bank")}</option>
              <option value="fiat_card">{railLabel("fiat_card")}</option>
            </select>
          </div>

          {rail === "crypto" && (
            <div className="wlt-field">
              <label className="wlt-label" htmlFor="wd-wallet">Wallet address</label>
              <input
                id="wd-wallet"
                className="wlt-input"
                type="text"
                placeholder="0x…"
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value)}
              />
            </div>
          )}

          {parsedAmount > 0 && (
            <div className="wlt-fee-preview">
              <div className="wlt-fee-row">
                <span className="wlt-fee-label">Amount</span>
                <span className="wlt-fee-value">${fmt(parsedAmount)}</span>
              </div>
              <div className="wlt-fee-row">
                <span className="wlt-fee-label">Fee (0.5%)</span>
                <span className="wlt-fee-value">−${fmt(withdrawalFee)}</span>
              </div>
              <div className="wlt-fee-row">
                <span className="wlt-fee-label">You receive</span>
                <span className="wlt-fee-value">${fmt(withdrawalNet)}</span>
              </div>
            </div>
          )}

          <p className="wlt-note">Min ${MIN_WITHDRAWAL} · Max ${MAX_WITHDRAWAL.toLocaleString()}</p>

          {error && <p className="wlt-note" style={{ color: "var(--no)" }}>{error}</p>}
          {success && <p className="wlt-note" style={{ color: "var(--yes)" }}>{success}</p>}

          <button className="wlt-submit" type="submit" disabled={!canSubmitWithdraw || submitting}>
            {submitting ? "Submitting…" : "Withdraw"}
          </button>
        </form>
      )}

      <div className="wlt-history">
        <h3>Transaction history</h3>
        {loadingHistory ? (
          <div className="wlt-loading">Loading history…</div>
        ) : transfers.length === 0 ? (
          <p className="wlt-note">No transactions yet.</p>
        ) : (
          <table className="wlt-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Rail</th>
                <th className="wlt-td-num">Amount</th>
                <th className="wlt-td-num">Fee</th>
                <th className="wlt-td-num">Net</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {transfers.map((t) => (
                <tr key={t.id}>
                  <td>
                    <span className={`wlt-badge ${t.direction === "deposit" ? "wlt-badge-deposit" : "wlt-badge-withdrawal"}`}>
                      {t.direction}
                    </span>
                  </td>
                  <td>{t.rail}</td>
                  <td className="wlt-td-num">${fmt(t.amount)}</td>
                  <td className="wlt-td-num">${fmt(t.fee_amount)}</td>
                  <td className="wlt-td-num">${fmt(t.net_amount)}</td>
                  <td>
                    <span className={statusClass(t.status)}>{t.status}</span>
                  </td>
                  <td>{formatDate(t.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
