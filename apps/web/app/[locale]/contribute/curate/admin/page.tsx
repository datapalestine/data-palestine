"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ──────────────────────────────────────────────

interface PendingReview {
  id: string;
  dataset_name: string;
  reviewer_name: string;
  submitted_at: string;
  change_count: number;
}

interface IndicatorDiff {
  indicator_id: string;
  current_name: string;
  proposed_name: string;
  action: "keep" | "rename" | "delete" | "merge";
}

interface ReviewDetail {
  id: string;
  dataset_id: string;
  dataset_name: string;
  proposed_name: string;
  proposed_description: string;
  proposed_category: string;
  flag_duplicate: boolean;
  reviewer_name: string;
  reviewer_email: string;
  notes: string;
  submitted_at: string;
  indicator_edits: IndicatorDiff[];
}

// ─── Helpers ────────────────────────────────────────────

function actionColor(action: string): string {
  switch (action) {
    case "rename":
      return "text-blue-700 bg-blue-50";
    case "delete":
      return "text-red-700 bg-red-50";
    case "merge":
      return "text-purple-700 bg-purple-50";
    default:
      return "text-neutral-500 bg-neutral-50";
  }
}

// ─── Component ──────────────────────────────────────────

export default function CurationAdminPage() {
  const t = useTranslations("contribute.curate.admin");
  const locale = useLocale();

  // Auth
  const [authKey, setAuthKey] = useState("");
  const [authInput, setAuthInput] = useState("");
  const [authenticated, setAuthenticated] = useState(false);

  // Reviews list
  const [reviews, setReviews] = useState<PendingReview[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected review detail
  const [selectedReview, setSelectedReview] = useState<ReviewDetail | null>(
    null,
  );
  const [detailLoading, setDetailLoading] = useState(false);

  // Reject
  const [rejectReason, setRejectReason] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  // Action state
  const [actionLoading, setActionLoading] = useState(false);

  // ─── Auth ──────────────────────────────────────────

  useEffect(() => {
    const stored = localStorage.getItem("dp_admin_key");
    if (stored) {
      setAuthKey(stored);
      setAuthenticated(true);
    }
  }, []);

  const handleAuth = () => {
    if (authInput.trim()) {
      localStorage.setItem("dp_admin_key", authInput.trim());
      setAuthKey(authInput.trim());
      setAuthenticated(true);
    }
  };

  const clearAuth = () => {
    localStorage.removeItem("dp_admin_key");
    setAuthKey("");
    setAuthenticated(false);
    setReviews([]);
    setSelectedReview(null);
  };

  const authHeaders = useCallback(
    (): Record<string, string> => ({
      Authorization: `Bearer ${authKey}`,
      "Content-Type": "application/json",
    }),
    [authKey],
  );

  const handleUnauthorized = () => {
    clearAuth();
    setError("Unauthorized. Please enter a valid admin key.");
  };

  // ─── Fetch reviews ────────────────────────────────

  const loadReviews = useCallback(async () => {
    if (!authKey) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/curation/reviews?lang=${locale}`,
        { headers: authHeaders() },
      );
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data: { data: PendingReview[] } = await res.json();
      setReviews(data.data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reviews");
    } finally {
      setLoading(false);
    }
  }, [authKey, locale, authHeaders]);

  useEffect(() => {
    if (authenticated) {
      loadReviews();
    }
  }, [authenticated, loadReviews]);

  // ─── Fetch review detail ──────────────────────────

  const loadReviewDetail = async (id: string) => {
    setDetailLoading(true);
    setShowRejectForm(false);
    setRejectReason("");
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/curation/reviews/${id}?lang=${locale}`,
        { headers: authHeaders() },
      );
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data: { data: ReviewDetail } = await res.json();
      setSelectedReview(data.data);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load review detail",
      );
    } finally {
      setDetailLoading(false);
    }
  };

  // ─── Approve / Reject ─────────────────────────────

  const handleApprove = async () => {
    if (!selectedReview) return;
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/curation/approve/${selectedReview.id}`,
        { method: "POST", headers: authHeaders() },
      );
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) throw new Error(`API ${res.status}`);
      setSelectedReview(null);
      loadReviews();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve");
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedReview) return;
    setActionLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/curation/reject/${selectedReview.id}`,
        {
          method: "POST",
          headers: authHeaders(),
          body: JSON.stringify({ reason: rejectReason }),
        },
      );
      if (res.status === 401) {
        handleUnauthorized();
        return;
      }
      if (!res.ok) throw new Error(`API ${res.status}`);
      setSelectedReview(null);
      setShowRejectForm(false);
      setRejectReason("");
      loadReviews();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject");
    } finally {
      setActionLoading(false);
    }
  };

  // ─── Auth prompt ───────────────────────────────────

  if (!authenticated) {
    return (
      <div className="min-h-screen bg-[#FAFAFA]">
        <div className="border-b border-neutral-200 bg-white">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
            <h1 className="text-xl font-bold text-neutral-900">
              {t("title")}
            </h1>
          </div>
        </div>
        <div className="mx-auto max-w-md px-4 py-16">
          <div className="rounded-lg border border-neutral-200 bg-white p-8">
            <label className="block text-sm font-medium text-neutral-700 mb-2">
              {t("enterKey")}
            </label>
            <input
              type="password"
              value={authInput}
              onChange={(e) => setAuthInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAuth()}
              className="mb-4 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32]"
              placeholder="Admin key"
            />
            {error && (
              <p className="mb-3 text-sm text-red-600">{error}</p>
            )}
            <button
              onClick={handleAuth}
              className="w-full rounded-md bg-[#2E7D32] px-4 py-2 text-sm font-medium text-white hover:bg-[#1B5E20] transition-colors"
            >
              Submit
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Main admin view ──────────────────────────────

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      {/* Header */}
      <div className="border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <h1 className="text-xl font-bold text-neutral-900">{t("title")}</h1>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {error && (
          <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
            {error}
          </div>
        )}

        {/* Review detail */}
        {selectedReview ? (
          <div>
            <button
              onClick={() => setSelectedReview(null)}
              className="mb-4 text-sm text-[#2E7D32] hover:underline"
            >
              &larr; Back to reviews
            </button>

            <div className="rounded-lg border border-neutral-200 bg-white p-6">
              <div className="mb-4 flex items-start justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-neutral-900">
                    {selectedReview.dataset_name}
                  </h2>
                  <p className="text-xs text-neutral-500 mt-1">
                    Reviewed by {selectedReview.reviewer_name} on{" "}
                    {new Date(selectedReview.submitted_at).toLocaleDateString()}
                  </p>
                </div>
                {selectedReview.flag_duplicate && (
                  <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700">
                    Flagged as duplicate
                  </span>
                )}
              </div>

              {/* Dataset-level diff */}
              <div className="mb-6 space-y-3 border-b border-neutral-100 pb-6">
                <h3 className="text-sm font-medium text-neutral-700">
                  Dataset Changes
                </h3>
                <div className="grid gap-2 text-sm">
                  <div className="flex gap-2">
                    <span className="w-24 shrink-0 text-xs text-neutral-500">
                      Name
                    </span>
                    {selectedReview.dataset_name !==
                    selectedReview.proposed_name ? (
                      <span>
                        <span className="line-through text-neutral-400">
                          {selectedReview.dataset_name}
                        </span>{" "}
                        <span className="text-green-700 font-medium">
                          {selectedReview.proposed_name}
                        </span>
                      </span>
                    ) : (
                      <span className="text-neutral-600">
                        {selectedReview.dataset_name}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <span className="w-24 shrink-0 text-xs text-neutral-500">
                      Category
                    </span>
                    <span className="text-neutral-600">
                      {selectedReview.proposed_category}
                    </span>
                  </div>
                </div>
                {selectedReview.notes && (
                  <div className="mt-2 rounded bg-neutral-50 p-3 text-xs text-neutral-600">
                    <span className="font-medium">Notes:</span>{" "}
                    {selectedReview.notes}
                  </div>
                )}
              </div>

              {/* Indicator diffs */}
              <h3 className="mb-3 text-sm font-medium text-neutral-700">
                Indicator Changes ({selectedReview.indicator_edits.length})
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-neutral-200 text-left text-xs text-neutral-500">
                      <th className="pb-2 pe-4 font-medium">Current Name</th>
                      <th className="pb-2 pe-4 font-medium">Proposed Name</th>
                      <th className="pb-2 font-medium">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedReview.indicator_edits.map((edit) => (
                      <tr
                        key={edit.indicator_id}
                        className="border-b border-neutral-100"
                      >
                        <td className="py-2 pe-4 text-xs text-neutral-600 max-w-[250px] break-words">
                          {edit.current_name}
                        </td>
                        <td className="py-2 pe-4 text-xs max-w-[250px] break-words">
                          {edit.proposed_name !== edit.current_name ? (
                            <span className="text-green-700 font-medium">
                              {edit.proposed_name}
                            </span>
                          ) : (
                            <span className="text-neutral-600">
                              {edit.proposed_name}
                            </span>
                          )}
                        </td>
                        <td className="py-2">
                          <span
                            className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${actionColor(edit.action)}`}
                          >
                            {edit.action}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Action buttons */}
              <div className="mt-6 flex items-center gap-3 border-t border-neutral-100 pt-6">
                <button
                  onClick={handleApprove}
                  disabled={actionLoading}
                  className="rounded-md bg-[#2E7D32] px-5 py-2 text-sm font-medium text-white hover:bg-[#1B5E20] disabled:opacity-50 transition-colors"
                >
                  {actionLoading ? "Processing..." : t("approve")}
                </button>
                {showRejectForm ? (
                  <div className="flex items-center gap-2 flex-1">
                    <input
                      type="text"
                      value={rejectReason}
                      onChange={(e) => setRejectReason(e.target.value)}
                      placeholder="Reason for rejection..."
                      className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm focus:border-red-500 focus:outline-none focus:ring-1 focus:ring-red-500"
                    />
                    <button
                      onClick={handleReject}
                      disabled={actionLoading || !rejectReason.trim()}
                      className="rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => {
                        setShowRejectForm(false);
                        setRejectReason("");
                      }}
                      className="text-sm text-neutral-500 hover:text-neutral-700"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowRejectForm(true)}
                    className="rounded-md border border-red-300 px-5 py-2 text-sm font-medium text-red-700 hover:bg-red-50 transition-colors"
                  >
                    {t("reject")}
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          /* Reviews list */
          <div>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <div
                    key={i}
                    className="h-16 animate-pulse rounded-lg bg-neutral-100"
                  />
                ))}
              </div>
            ) : reviews.length === 0 ? (
              <div className="text-center py-12 text-neutral-500 text-sm">
                No pending reviews.
              </div>
            ) : (
              <div className="space-y-2">
                {reviews.map((review) => (
                  <button
                    key={review.id}
                    onClick={() => loadReviewDetail(review.id)}
                    className="w-full text-start rounded-lg border border-neutral-200 bg-white p-4 hover:border-[#2E7D32] hover:shadow-sm transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-medium text-neutral-900">
                          {review.dataset_name}
                        </h3>
                        <p className="mt-0.5 text-xs text-neutral-500">
                          by {review.reviewer_name} &middot;{" "}
                          {new Date(review.submitted_at).toLocaleDateString()}
                        </p>
                      </div>
                      <span className="rounded-full bg-neutral-100 px-3 py-1 text-xs font-medium text-neutral-600">
                        {review.change_count} changes
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}

            {detailLoading && (
              <div className="mt-4 h-64 animate-pulse rounded-lg bg-neutral-100" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
