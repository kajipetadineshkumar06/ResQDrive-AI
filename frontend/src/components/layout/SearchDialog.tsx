import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/axios";
import Icon, { type IconName } from "../ui/Icon";

interface SearchRecord {
  id: string;
  title: string;
  description: string;
  path: string;
  icon: IconName;
}

interface Vehicle { vehicle_id: number; make: string; model: string; plate_number: string; }
interface Emergency { emergency_id: number; emergency_type: string; description: string | null; status: string; }
interface Request { request_id: number; emergency_id: number; request_status: string; notes: string | null; }

const sections: SearchRecord[] = [
  { id: "dashboard", title: "Dashboard", description: "Your customer overview", path: "/dashboard", icon: "dashboard" },
  { id: "vehicles", title: "My Vehicles", description: "View and manage your vehicles", path: "/vehicles", icon: "car" },
  { id: "requests", title: "Service Requests", description: "View your service requests", path: "/service-requests", icon: "clipboard" },
  { id: "emergency", title: "Emergency Assistance", description: "Request roadside help", path: "/emergency", icon: "siren" },
  { id: "tracking", title: "Live Tracking", description: "Track an active service request", path: "/tracking", icon: "mapPin" },
  { id: "ai", title: "AI Assistant", description: "Get help understanding a vehicle problem", path: "/ai", icon: "bot" },
  { id: "history", title: "Service History", description: "Past emergencies and service requests", path: "/history", icon: "history" },
  { id: "notifications", title: "Notifications", description: "Updates about your requests", path: "/notifications", icon: "bell" },
];

export default function SearchDialog({ onClose }: { onClose: () => void }) {
  const [query, setQuery] = useState("");
  const [records, setRecords] = useState<SearchRecord[]>(sections);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    let active = true;
    Promise.all([
      api.get<Vehicle[]>("/vehicles/"),
      api.get<Emergency[]>("/emergencies/"),
      api.get<Request[]>("/service-requests/"),
    ]).then(([vehicles, emergencies, requests]) => {
      if (!active) return;
      const items: SearchRecord[] = [
        ...vehicles.data.map((v) => ({ id: `vehicle-${v.vehicle_id}`, title: `${v.make} ${v.model}`, description: v.plate_number, path: "/vehicles", icon: "car" as const })),
        ...emergencies.data.map((e) => ({ id: `emergency-${e.emergency_id}`, title: `Emergency #${e.emergency_id}: ${e.emergency_type.replace(/_/g, " ")}`, description: [e.description, e.status].filter(Boolean).join(" · "), path: "/history", icon: "siren" as const })),
        ...requests.data.map((r) => ({ id: `request-${r.request_id}`, title: `Service request #${r.request_id}`, description: [r.request_status, r.notes].filter(Boolean).join(" · "), path: "/service-requests", icon: "clipboard" as const })),
      ];
      setRecords([...sections, ...items]);
    }).catch((reason: unknown) => {
      console.error("Search content loading error:", reason);
      if (active) setError("Your saved vehicles and requests could not be loaded. You can still search the available pages.");
    }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  const results = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return (normalized ? records.filter((record) => `${record.title} ${record.description}`.toLowerCase().includes(normalized)) : sections)
      .slice(0, 12);
  }, [query, records]);

  const openResult = (path: string) => { onClose(); navigate(path); };

  return (
    <div className="search-overlay" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="search-dialog" role="dialog" aria-modal="true" aria-labelledby="search-title">
        <div className="search-dialog-heading">
          <h2 id="search-title">Search ResQDrive</h2>
          <button type="button" onClick={onClose} aria-label="Close search"><Icon name="close" /></button>
        </div>
        <input autoFocus type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search pages, vehicles, emergencies, requests…" aria-label="Search customer content" />
        {error && <p className="search-message" role="status">{error}</p>}
        {loading && <p className="search-message" role="status">Loading your saved content…</p>}
        <div className="search-results" role="listbox" aria-label="Search results">
          {results.map((result) => (
            <button type="button" role="option" aria-selected="false" className="search-result" key={result.id} onClick={() => openResult(result.path)}>
              <Icon name={result.icon} />
              <span className="search-result-copy">
              <strong>{result.title}</strong><span>{result.description}</span>
              </span>
            </button>
          ))}
          {!loading && query.trim() && results.length === 0 && <p className="search-message">No matching customer content found.</p>}
        </div>
      </section>
    </div>
  );
}
