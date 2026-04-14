"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/auth-provider";
import { sattaApiFetch } from "@/lib/api/beyul-api";
import type { Notification, NotificationListResponse, NotificationUnreadCount } from "@/lib/api/types";

const POLL_INTERVAL_MS = 30_000;
const PAGE_SIZE = 20;

const NOTIFICATION_ICON_MAP: Record<string, string> = {
  order_filled: "✓",
  order_cancelled: "✕",
  order_rejected: "!",
  market_opened: "▶",
  market_settled: "◆",
  market_cancelled: "—",
  market_disputed: "⚠",
  settlement_requested: "⏱",
  settlement_finalized: "◆",
  price_alert: "⚡",
  system: "ℹ",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export const NotificationBell = () => {
  const { user, getAccessToken } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchUnreadCount = useCallback(async () => {
    if (!user) return;
    try {
      const token = await getAccessToken();
      if (!token) return;
      const data = await sattaApiFetch<NotificationUnreadCount>("/api/v1/notifications/unread-count", {
        accessToken: token,
      });
      setUnreadCount(data.unread_count);
    } catch {
      // silent
    }
  }, [user, getAccessToken]);

  const fetchNotifications = useCallback(async () => {
    if (!user) return;
    setIsLoading(true);
    try {
      const token = await getAccessToken();
      if (!token) return;
      const data = await sattaApiFetch<NotificationListResponse>(
        `/api/v1/notifications?limit=${PAGE_SIZE}&offset=0`,
        { accessToken: token }
      );
      setItems(data.items);
      setUnreadCount(data.unread_count);
    } catch {
      // silent
    } finally {
      setIsLoading(false);
    }
  }, [user, getAccessToken]);

  const markAllRead = useCallback(async () => {
    if (!user || unreadCount === 0) return;
    try {
      const token = await getAccessToken();
      if (!token) return;
      await sattaApiFetch("/api/v1/notifications/mark-read", {
        accessToken: token,
        method: "POST",
        json: { mark_all: true },
      });
      setUnreadCount(0);
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      // silent
    }
  }, [user, getAccessToken, unreadCount]);

  useEffect(() => {
    if (!user) {
      setUnreadCount(0);
      setItems([]);
      return;
    }
    void fetchUnreadCount();
    pollRef.current = setInterval(fetchUnreadCount, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [user, fetchUnreadCount]);

  useEffect(() => {
    if (isOpen) {
      void fetchNotifications();
    }
  }, [isOpen, fetchNotifications]);

  useEffect(() => {
    const handlePointerDown = (event: MouseEvent) => {
      if (!dropdownRef.current?.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, []);

  if (!user) return null;

  return (
    <div className="notif-bell-container" ref={dropdownRef}>
      <button
        className="notif-bell-btn"
        type="button"
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M12 2a7 7 0 0 0-7 7v3.528c0 .33-.132.648-.366.882L3.22 14.824A1.5 1.5 0 0 0 4.28 17h15.44a1.5 1.5 0 0 0 1.06-2.176l-1.414-1.414A1.25 1.25 0 0 1 19 12.528V9a7 7 0 0 0-7-7Z"
            stroke="currentColor"
            strokeWidth="1.5"
          />
          <path d="M9 17a3 3 0 1 0 6 0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
        {unreadCount > 0 ? (
          <span className="notif-bell-badge" aria-hidden="true">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className="notif-dropdown" role="menu">
          <div className="notif-dropdown-header">
            <strong>Notifications</strong>
            {unreadCount > 0 ? (
              <button className="notif-mark-all-btn" type="button" onClick={markAllRead}>
                Mark all read
              </button>
            ) : null}
          </div>

          {isLoading && items.length === 0 ? (
            <div className="notif-dropdown-empty">Loading...</div>
          ) : items.length === 0 ? (
            <div className="notif-dropdown-empty">No notifications yet</div>
          ) : (
            <div className="notif-dropdown-list">
              {items.map((notif) => (
                <NotificationItem key={notif.id} notif={notif} onClose={() => setIsOpen(false)} />
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};

const NotificationItem = ({ notif, onClose }: { notif: Notification; onClose: () => void }) => {
  const icon = NOTIFICATION_ICON_MAP[notif.kind] || "•";
  const content = (
    <div className={`notif-item ${notif.is_read ? "" : "notif-item-unread"}`}>
      <span className="notif-item-icon" aria-hidden="true">{icon}</span>
      <div className="notif-item-content">
        <span className="notif-item-title">{notif.title}</span>
        {notif.body ? <span className="notif-item-body">{notif.body}</span> : null}
        <span className="notif-item-time">{timeAgo(notif.created_at)}</span>
      </div>
    </div>
  );

  if (notif.market_slug) {
    return (
      <Link
        href={`/markets/${notif.market_slug}`}
        className="notif-item-link"
        onClick={onClose}
      >
        {content}
      </Link>
    );
  }

  return content;
};
