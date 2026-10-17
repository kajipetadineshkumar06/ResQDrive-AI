import { useEffect, useState } from "react";
import AppLayout from "../components/layout/AppLayout";
import api from "../api/axios";

interface Emergency {
  emergency_id: number;
  emergency_type: string;
  description: string | null;
  priority: string;
  status: string;
  created_at: string;
}

interface ServiceRequest {
  request_id: number;
  emergency_id: number;
  request_status: string;
  notes: string | null;
  requested_at: string;
}

type HistoryEntry = {
  id: string;
  kind: "Emergency" | "Service request";
  summary: string;
  detail: string;
  status: string;
  date: string;
};

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export default function History() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get<Emergency[]>("/emergencies/"),
      api.get<ServiceRequest[]>("/service-requests/"),
    ])
      .then(([emergenciesResponse, requestsResponse]) => {
        if (!active) return;
        const emergencies: HistoryEntry[] = emergenciesResponse.data.map((item) => ({
          id: `emergency-${item.emergency_id}`,
          kind: "Emergency",
          summary: item.emergency_type.replace(/_/g, " "),
          detail: item.description || `Priority: ${item.priority}`,
          status: item.status,
          date: item.created_at,
        }));
        const requests: HistoryEntry[] = requestsResponse.data.map((item) => ({
          id: `request-${item.request_id}`,
          kind: "Service request",
          summary: `Request #${item.request_id}`,
          detail: item.notes || `Emergency #${item.emergency_id}`,
          status: item.request_status,
          date: item.requested_at,
        }));
        setEntries([...emergencies, ...requests].sort(
          (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime(),
        ));
      })
      .catch((reason: unknown) => {
        console.error("History loading error:", reason);
        if (active) setError("Unable to load your history. Please try again later.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  return (
    <AppLayout>
      <div className="history-page">
        <div className="history-heading">
          <span className="eyebrow">YOUR ACTIVITY</span>
          <h2>Service History</h2>
          <p>Past emergencies and service requests on your account.</p>
        </div>
        {loading ? (
          <div className="history-state" role="status">Loading your history…</div>
        ) : error ? (
          <div className="history-state history-error" role="alert">{error}</div>
        ) : entries.length === 0 ? (
          <div className="history-state">No past emergencies or service requests yet.</div>
        ) : (
          <div className="history-list">
            {entries.map((entry) => (
              <article className="history-card" key={entry.id}>
                <div className="history-card-main">
                  <span className="history-kind">{entry.kind}</span>
                  <h3>{entry.summary}</h3>
                  <p>{entry.detail}</p>
                </div>
                <div className="history-card-meta">
                  <span className="history-status">{entry.status.replace(/_/g, " ")}</span>
                  <time dateTime={entry.date}>{formatDate(entry.date)}</time>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
