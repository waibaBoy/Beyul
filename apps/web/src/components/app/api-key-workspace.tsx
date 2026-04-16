"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/components/auth/auth-provider";
import { beyulApiFetch } from "@/lib/api/beyul-api";

type ApiKey = {
  id: string;
  label: string;
  key_prefix: string;
  permissions: string[];
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
};

type CreateKeyResponse = ApiKey & { key: string };

const fmtDate = (v: string | null) => {
  if (!v) return "—";
  return new Date(v).toLocaleDateString([], {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
};

export const ApiKeyWorkspace = () => {
  const { session, isReady } = useAuth();
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [label, setLabel] = useState("");
  const [perms, setPerms] = useState<Record<string, boolean>>({
    read: true,
    trade: false,
  });
  const [creating, setCreating] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchKeys = useCallback(async () => {
    if (!session?.access_token) return;
    try {
      const res = await beyulApiFetch<{ keys: ApiKey[]; count: number }>(
        "/api/v1/api-keys",
        { accessToken: session.access_token }
      );
      setKeys(res.keys);
    } catch {
      /* silent */
    } finally {
      setIsLoading(false);
    }
  }, [session?.access_token]);

  useEffect(() => {
    if (isReady && session?.access_token) {
      void fetchKeys();
    } else if (isReady) {
      setIsLoading(false);
    }
  }, [isReady, session?.access_token, fetchKeys]);

  if (!isReady) return <div className="ak-loading">Loading…</div>;
  if (!session) {
    return <div className="ak-empty">Sign in to manage API keys.</div>;
  }

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setNewKey(null);
    const selectedPerms = Object.entries(perms)
      .filter(([, v]) => v)
      .map(([k]) => k);

    if (!label.trim()) {
      setError("Label is required.");
      return;
    }
    if (selectedPerms.length === 0) {
      setError("Select at least one permission.");
      return;
    }

    setCreating(true);
    try {
      const res = await beyulApiFetch<CreateKeyResponse>("/api/v1/api-keys", {
        method: "POST",
        accessToken: session.access_token,
        json: { label: label.trim(), permissions: selectedPerms },
      });
      setNewKey(res.key);
      setLabel("");
      setPerms({ read: true, trade: false });
      void fetchKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create key.");
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!newKey) return;
    await navigator.clipboard.writeText(newKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRevoke = async (keyId: string) => {
    try {
      await beyulApiFetch(`/api/v1/api-keys/${keyId}`, {
        method: "DELETE",
        accessToken: session.access_token,
      });
      setRevoking(null);
      void fetchKeys();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to revoke key.");
      setRevoking(null);
    }
  };

  return (
    <div className="ak-shell">
      <form className="ak-create-form" onSubmit={handleCreate}>
        <div className="ak-field">
          <label className="ak-label" htmlFor="ak-label-input">
            Label
          </label>
          <input
            id="ak-label-input"
            className="ak-input"
            type="text"
            placeholder="e.g. Trading Bot"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>

        <div className="ak-field">
          <span className="ak-label">Permissions</span>
          <div className="ak-perms">
            {(["read", "trade"] as const).map((p) => (
              <label key={p} className="ak-perm-label">
                <input
                  type="checkbox"
                  checked={perms[p]}
                  onChange={(e) =>
                    setPerms((prev) => ({ ...prev, [p]: e.target.checked }))
                  }
                />
                {p.charAt(0).toUpperCase() + p.slice(1)}
              </label>
            ))}
          </div>
        </div>

        {error && (
          <div style={{ color: "#ef4444", fontSize: "0.82rem" }}>{error}</div>
        )}

        <button className="ak-submit" type="submit" disabled={creating}>
          {creating ? "Creating…" : "Create API Key"}
        </button>
      </form>

      {newKey && (
        <div className="ak-new-key-box">
          <div className="ak-new-key-title">Your new API key</div>
          <div className="ak-new-key-value">{newKey}</div>
          <div className="ak-new-key-warn">
            Copy this key now — it will not be shown again.
          </div>
          <button className="ak-copy-btn" type="button" onClick={handleCopy}>
            {copied ? "Copied!" : "Copy to clipboard"}
          </button>
        </div>
      )}

      {isLoading ? (
        <div className="ak-loading">Loading keys…</div>
      ) : keys.length === 0 ? (
        <div className="ak-empty">No API keys yet. Create one above.</div>
      ) : (
        <table className="ak-table">
          <thead>
            <tr>
              <th>Label</th>
              <th>Key</th>
              <th>Permissions</th>
              <th>Status</th>
              <th>Last Used</th>
              <th>Created</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {keys.map((k) => (
              <tr key={k.id}>
                <td>{k.label}</td>
                <td>
                  <span className="ak-key-prefix">{k.key_prefix}•••</span>
                </td>
                <td>{k.permissions.join(", ")}</td>
                <td>
                  <span
                    className={
                      k.is_active ? "ak-badge-active" : "ak-badge-revoked"
                    }
                  >
                    {k.is_active ? "Active" : "Revoked"}
                  </span>
                </td>
                <td>{fmtDate(k.last_used_at)}</td>
                <td>{fmtDate(k.created_at)}</td>
                <td>
                  {k.is_active &&
                    (revoking === k.id ? (
                      <span style={{ display: "flex", gap: 6 }}>
                        <button
                          className="ak-revoke-btn"
                          type="button"
                          onClick={() => handleRevoke(k.id)}
                        >
                          Confirm
                        </button>
                        <button
                          className="ak-copy-btn"
                          type="button"
                          onClick={() => setRevoking(null)}
                        >
                          Cancel
                        </button>
                      </span>
                    ) : (
                      <button
                        className="ak-revoke-btn"
                        type="button"
                        onClick={() => setRevoking(k.id)}
                      >
                        Revoke
                      </button>
                    ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};
