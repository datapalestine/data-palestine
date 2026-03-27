"use client";

import { useCallback, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Types ──────────────────────────────────────────────

interface QueueItem {
  id: string;
  name: string;
  source_name: string;
  indicator_count: number;
  observation_count: number;
}

interface QueueResponse {
  data: QueueItem[];
  meta: { total: number; reviewed: number; remaining: number };
}

interface SampleObservation {
  period: string;
  geography: string;
  indicator: string;
  value: number | null;
}

interface IndicatorItem {
  id: string;
  name: string;
  observation_count: number;
}

interface DatasetCurationDetail {
  id: string;
  name: string;
  description: string;
  category: string;
  source_name: string;
  source_url: string;
  categories: string[];
  indicators: IndicatorItem[];
  sample_observations: SampleObservation[];
}

interface IndicatorEdit {
  id: string;
  current_name: string;
  proposed_name: string;
  action: "keep" | "rename" | "delete" | "merge";
  observation_count: number;
  highlight: boolean;
}

// ─── Smart suggestion helpers ───────────────────────────

function suggestName(name: string): { proposed: string; highlight: boolean } {
  let proposed = name;
  let highlight = false;

  // Unclosed parenthesis at end
  if (/\([^)]*$/.test(proposed)) {
    proposed = proposed.replace(/\s*\([^)]*$/, "").trim();
    highlight = true;
  }

  // Starts with "N. " pattern (numbered prefix)
  if (/^\d+\.\s+/.test(proposed)) {
    proposed = proposed.replace(/^\d+\.\s+/, "");
    highlight = true;
  }

  // Contains a year like 2020
  if (/\b(19|20)\d{2}\b/.test(proposed)) {
    highlight = true;
  }

  return { proposed, highlight };
}

// ─── Component ──────────────────────────────────────────

export default function CuratePage() {
  const t = useTranslations("contribute.curate");
  const locale = useLocale();

  // Queue state
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [queueMeta, setQueueMeta] = useState<{
    total: number;
    reviewed: number;
    remaining: number;
  }>({ total: 0, reviewed: 0, remaining: 0 });
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dataset detail
  const [dataset, setDataset] = useState<DatasetCurationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Editable fields
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [flagDuplicate, setFlagDuplicate] = useState(false);
  const [indicators, setIndicators] = useState<IndicatorEdit[]>([]);

  // Submission
  const [reviewerName, setReviewerName] = useState("");
  const [reviewerEmail, setReviewerEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  // ─── Fetch queue ────────────────────────────────────

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/v1/curation/queue?lang=${locale}`,
      );
      if (!res.ok) throw new Error(`API ${res.status}`);
      const data: QueueResponse = await res.json();
      setQueue(data.data);
      setQueueMeta(data.meta);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load queue");
    } finally {
      setLoading(false);
    }
  }, [locale]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  // ─── Fetch dataset detail ──────────────────────────

  const loadDataset = useCallback(
    async (id: string) => {
      setDetailLoading(true);
      setSuccess(false);
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/curation/dataset/${id}?lang=${locale}`,
        );
        if (!res.ok) throw new Error(`API ${res.status}`);
        const data: { data: DatasetCurationDetail } = await res.json();
        const d = data.data;
        setDataset(d);
        setEditName(d.name);
        setEditDescription(d.description);
        setEditCategory(d.category);
        setFlagDuplicate(false);

        // Build indicator edits with smart suggestions
        setIndicators(
          d.indicators.map((ind) => {
            const { proposed, highlight } = suggestName(ind.name);
            return {
              id: ind.id,
              current_name: ind.name,
              proposed_name: proposed,
              action: proposed !== ind.name ? "rename" : "keep",
              observation_count: ind.observation_count,
              highlight,
            };
          }),
        );
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load dataset",
        );
      } finally {
        setDetailLoading(false);
      }
    },
    [locale],
  );

  useEffect(() => {
    if (queue.length > 0 && currentIndex < queue.length) {
      loadDataset(queue[currentIndex].id);
    }
  }, [queue, currentIndex, loadDataset]);

  // ─── Handlers ──────────────────────────────────────

  const handleSkip = () => {
    if (currentIndex < queue.length - 1) {
      setCurrentIndex((i) => i + 1);
    }
  };

  const handleSubmit = async () => {
    if (!dataset) return;
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        dataset_id: dataset.id,
        proposed_name: editName,
        proposed_description: editDescription,
        proposed_category: editCategory,
        flag_duplicate: flagDuplicate,
        reviewer_name: reviewerName,
        reviewer_email: reviewerEmail,
        notes,
        indicator_edits: indicators.map((ind) => ({
          indicator_id: ind.id,
          proposed_name: ind.proposed_name,
          action: ind.action,
        })),
      };
      const res = await fetch(`${API_BASE}/api/v1/curation/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error(`API ${res.status}`);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit review");
    } finally {
      setSubmitting(false);
    }
  };

  const updateIndicator = (
    id: string,
    field: keyof IndicatorEdit,
    value: string,
  ) => {
    setIndicators((prev) =>
      prev.map((ind) => (ind.id === id ? { ...ind, [field]: value } : ind)),
    );
  };

  // ─── Render ────────────────────────────────────────

  const reviewed = queueMeta.total - queueMeta.remaining;
  const progressPct =
    queueMeta.total > 0 ? (reviewed / queueMeta.total) * 100 : 0;

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAFAFA]">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
          <div className="h-8 w-64 animate-pulse rounded bg-neutral-200" />
          <div className="mt-4 h-96 animate-pulse rounded-lg bg-neutral-100" />
        </div>
      </div>
    );
  }

  if (error && !dataset) {
    return (
      <div className="min-h-screen bg-[#FAFAFA]">
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6">
          <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-800">
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div className="min-h-screen bg-[#FAFAFA]">
        <div className="border-b border-neutral-200 bg-white">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
            <h1 className="text-xl font-bold text-neutral-900">
              {t("title")}
            </h1>
            <p className="mt-1 text-sm text-neutral-500">{t("subtitle")}</p>
          </div>
        </div>
        <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 text-center text-neutral-500">
          All datasets have been reviewed. Thank you.
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAFAFA]">
      {/* Header */}
      <div className="border-b border-neutral-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
          <h1 className="text-xl font-bold text-neutral-900">{t("title")}</h1>
          <p className="mt-1 text-sm text-neutral-500">{t("subtitle")}</p>
        </div>
      </div>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="mb-2 flex items-center justify-between text-sm text-neutral-600">
            <span>
              {t("progress", {
                reviewed: String(reviewed),
                total: String(queueMeta.total),
              })}
            </span>
            <span className="text-xs text-neutral-400">
              {Math.round(progressPct)}%
            </span>
          </div>
          <div className="h-2.5 w-full overflow-hidden rounded-full bg-neutral-200">
            <div
              className="h-full rounded-full bg-[#2E7D32] transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        {detailLoading ? (
          <div className="h-96 animate-pulse rounded-lg bg-neutral-100" />
        ) : dataset ? (
          <>
            {/* Error banner */}
            {error && (
              <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
                {error}
              </div>
            )}

            {/* Success banner */}
            {success && (
              <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4 text-sm text-green-800">
                {t("success")}
              </div>
            )}

            {/* Main two-column area */}
            <div className="grid gap-6 lg:grid-cols-5">
              {/* Left column — dataset editing (60%) */}
              <div className="lg:col-span-3 space-y-5">
                <div className="rounded-lg border border-neutral-200 bg-white p-6">
                  <h2 className="mb-4 text-sm font-semibold text-neutral-900">
                    Dataset Details
                  </h2>

                  {/* Name */}
                  <label className="block text-xs font-medium text-neutral-600 mb-1">
                    Name
                  </label>
                  <input
                    type="text"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    className="mb-4 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32]"
                  />

                  {/* Description */}
                  <label className="block text-xs font-medium text-neutral-600 mb-1">
                    Description
                  </label>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={3}
                    className="mb-4 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32]"
                  />

                  {/* Category */}
                  <label className="block text-xs font-medium text-neutral-600 mb-1">
                    Category
                  </label>
                  <select
                    value={editCategory}
                    onChange={(e) => setEditCategory(e.target.value)}
                    className="mb-4 w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 bg-white focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32]"
                  >
                    {dataset.categories.map((cat) => (
                      <option key={cat} value={cat}>
                        {cat}
                      </option>
                    ))}
                  </select>

                  {/* Flag duplicate */}
                  <label className="flex items-center gap-2 text-sm text-neutral-700 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={flagDuplicate}
                      onChange={(e) => setFlagDuplicate(e.target.checked)}
                      className="h-4 w-4 rounded border-neutral-300 text-[#2E7D32] focus:ring-[#2E7D32]"
                    />
                    Flag as duplicate
                  </label>
                </div>
              </div>

              {/* Right column — source info & sample (40%) */}
              <div className="lg:col-span-2 space-y-5">
                {/* Source Info */}
                <div className="rounded-lg border border-neutral-200 bg-white p-6">
                  <h3 className="mb-3 text-sm font-semibold text-neutral-900">
                    Source Info
                  </h3>
                  <dl className="space-y-2 text-sm">
                    <div>
                      <dt className="text-xs text-neutral-500">Source</dt>
                      <dd className="text-neutral-800">
                        {dataset.source_name}
                      </dd>
                    </div>
                    {dataset.source_url && (
                      <div>
                        <dt className="text-xs text-neutral-500">URL</dt>
                        <dd>
                          <a
                            href={dataset.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-[#2E7D32] hover:underline break-all text-xs"
                          >
                            {dataset.source_url}
                          </a>
                        </dd>
                      </div>
                    )}
                  </dl>
                </div>

                {/* Sample Data */}
                <div className="rounded-lg border border-neutral-200 bg-white p-6">
                  <h3 className="mb-3 text-sm font-semibold text-neutral-900">
                    Sample Data
                  </h3>
                  {dataset.sample_observations.length === 0 ? (
                    <p className="text-xs text-neutral-400">
                      No sample data available.
                    </p>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-neutral-200 text-left text-neutral-500">
                            <th className="pb-2 pe-3 font-medium">Period</th>
                            <th className="pb-2 pe-3 font-medium">
                              Geography
                            </th>
                            <th className="pb-2 pe-3 font-medium">
                              Indicator
                            </th>
                            <th className="pb-2 font-medium text-end">
                              Value
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {dataset.sample_observations.map((obs, i) => (
                            <tr
                              key={i}
                              className="border-b border-neutral-100"
                            >
                              <td className="py-1.5 pe-3 text-neutral-700">
                                {obs.period}
                              </td>
                              <td className="py-1.5 pe-3 text-neutral-700">
                                {obs.geography}
                              </td>
                              <td className="py-1.5 pe-3 text-neutral-700 max-w-[150px] truncate">
                                {obs.indicator}
                              </td>
                              <td className="py-1.5 text-end text-neutral-900 font-medium tabular-nums">
                                {obs.value !== null
                                  ? obs.value.toLocaleString()
                                  : "\u2014"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Indicator editing table */}
            <div className="mt-8 rounded-lg border border-neutral-200 bg-white p-6">
              <h2 className="mb-4 text-sm font-semibold text-neutral-900">
                Indicators ({indicators.length})
              </h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-neutral-200 text-left text-xs text-neutral-500">
                      <th className="pb-2 pe-4 font-medium">Current Name</th>
                      <th className="pb-2 pe-4 font-medium">Proposed Name</th>
                      <th className="pb-2 pe-4 font-medium">Action</th>
                      <th className="pb-2 font-medium text-end">Obs Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {indicators.map((ind) => (
                      <tr
                        key={ind.id}
                        className={`border-b border-neutral-100 ${
                          ind.highlight ? "bg-yellow-50" : ""
                        }`}
                      >
                        {/* Current Name */}
                        <td className="py-2 pe-4 text-xs text-neutral-600 max-w-[250px]">
                          <span className="break-words">
                            {ind.current_name}
                          </span>
                        </td>

                        {/* Proposed Name */}
                        <td className="py-2 pe-4">
                          <input
                            type="text"
                            value={ind.proposed_name}
                            onChange={(e) =>
                              updateIndicator(
                                ind.id,
                                "proposed_name",
                                e.target.value,
                              )
                            }
                            className={`w-full rounded border px-2 py-1 text-xs text-neutral-900 focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32] ${
                              ind.highlight
                                ? "border-yellow-400 bg-yellow-50"
                                : "border-neutral-300"
                            }`}
                          />
                        </td>

                        {/* Action */}
                        <td className="py-2 pe-4">
                          <select
                            value={ind.action}
                            onChange={(e) =>
                              updateIndicator(ind.id, "action", e.target.value)
                            }
                            className="rounded border border-neutral-300 bg-white px-2 py-1 text-xs text-neutral-900 focus:border-[#2E7D32] focus:outline-none"
                          >
                            <option value="keep">Keep</option>
                            <option value="rename">Rename</option>
                            <option value="delete">Delete</option>
                            <option value="merge">Merge</option>
                          </select>
                        </td>

                        {/* Obs Count */}
                        <td className="py-2 text-end text-xs text-neutral-500 tabular-nums">
                          {ind.observation_count.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Submission section */}
            <div className="mt-8 rounded-lg border border-neutral-200 bg-white p-6">
              <h2 className="mb-4 text-sm font-semibold text-neutral-900">
                Submit Review
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-medium text-neutral-600 mb-1">
                    Your Name
                  </label>
                  <input
                    type="text"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-neutral-600 mb-1">
                    Your Email
                  </label>
                  <input
                    type="email"
                    value={reviewerEmail}
                    onChange={(e) => setReviewerEmail(e.target.value)}
                    className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32]"
                  />
                </div>
              </div>
              <div className="mt-4">
                <label className="block text-xs font-medium text-neutral-600 mb-1">
                  Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="w-full rounded-md border border-neutral-300 px-3 py-2 text-sm text-neutral-900 focus:border-[#2E7D32] focus:outline-none focus:ring-1 focus:ring-[#2E7D32]"
                  placeholder="Optional notes about this dataset..."
                />
              </div>
              <div className="mt-6 flex items-center gap-3">
                <button
                  onClick={handleSubmit}
                  disabled={submitting || !reviewerName || !reviewerEmail}
                  className="rounded-md bg-[#2E7D32] px-5 py-2 text-sm font-medium text-white hover:bg-[#1B5E20] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {submitting ? "Submitting..." : t("submit")}
                </button>
                <button
                  onClick={handleSkip}
                  disabled={currentIndex >= queue.length - 1}
                  className="rounded-md border border-neutral-300 bg-white px-5 py-2 text-sm font-medium text-neutral-700 hover:bg-neutral-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {t("skip")}
                </button>
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
