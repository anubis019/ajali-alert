import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity,
  AlertTriangle,
  Check,
  Copy,
  Cross,
  MapPin,
  Mic,
  MicOff,
  Phone,
  RefreshCw,
  Share2,
  ShieldAlert,
  Siren,
  X,
} from "lucide-react";
import { api, Incident, IncidentType, socketUrl, Topic } from "./api";
import { useVoiceAssistant } from "./voice";

/* ------------------------------------------------------------------ */
/* Constants                                                           */
/* ------------------------------------------------------------------ */

const INCIDENT_ID_KEY = "ajali_incident_id";
const DRAFT_KEY = "ajali_report_draft";
const WS_MAX_BACKOFF_MS = 30_000;
const WS_BASE_BACKOFF_MS = 1_500;

/** Fallback coordinates when GPS is denied (Nairobi CBD). */
const DEFAULT_COORDS = { lat: -1.286389, lng: 36.817223 };

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type Coords = { lat: number; lng: number; accuracy?: number };
type Connection = "connecting" | "live" | "offline";

interface Draft {
  selectedType: string;
  description: string;
  casualties: number;
  location: string;
  landmark: string;
}

const EMPTY_DRAFT: Draft = {
  selectedType: "",
  description: "",
  casualties: 0,
  location: "",
  landmark: "",
};

function loadDraft(): Draft {
  try {
    const raw = localStorage.getItem(DRAFT_KEY);
    if (!raw) return EMPTY_DRAFT;
    return { ...EMPTY_DRAFT, ...JSON.parse(raw) };
  } catch {
    return EMPTY_DRAFT;
  }
}

/* ------------------------------------------------------------------ */
/* Small presentational components                                     */
/* ------------------------------------------------------------------ */

function TopicList({ topics }: { topics: Topic[] }) {
  if (!topics.length) {
    return <p className="muted">No matching guidance. Add detail or ask a specific question.</p>;
  }
  return (
    <div>
      {topics.map((topic) => (
        <details className="topic" key={topic.id}>
          <summary>{topic.title}</summary>
          <ol>
            {topic.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
          {(topic.warnings || []).map((warning) => (
            <p className="muted" key={warning}>
              <AlertTriangle size={14} /> Warning: {warning}
            </p>
          ))}
        </details>
      ))}
    </div>
  );
}

function ConnectionBadge({ state }: { state: Connection }) {
  const label = state === "live" ? "Live" : state === "offline" ? "Reconnecting" : "Connecting";
  return (
    <div className={`live ${state}`} role="status" aria-live="polite">
      <span className="dot" />
      {label}
    </div>
  );
}

function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard unavailable — silently ignore */
    }
  }, [text]);

  useEffect(() => () => {
    if (timer.current) window.clearTimeout(timer.current);
  }, []);

  return (
    <button type="button" className="ghost-btn" onClick={handleCopy} aria-label={label}>
      {copied ? <Check size={14} /> : <Copy size={14} />}
      {copied ? "Copied" : label}
    </button>
  );
}

function Timeline({ incident }: { incident: Incident }) {
  // Support both `history` and `status_history` depending on backend schema
  const events = incident.history ?? (incident as unknown as { status_history?: typeof incident.history }).status_history ?? [];

  if (!events.length) {
    return <p className="muted">No status changes yet.</p>;
  }

  return (
    <ul className="timeline">
      {events
        .slice()
        .reverse()
        .map((event) => (
          <li key={`${event.status}-${event.created_at}`}>
            <strong>{event.status.replaceAll("_", " ")}</strong>
            <small>
              {event.note ? `${event.note} · ` : ""}
              {new Date(event.created_at).toLocaleTimeString([], {
                hour: "2-digit",
                minute: "2-digit",
              })}
            </small>
          </li>
        ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ */
/* Main App                                                            */
/* ------------------------------------------------------------------ */

export function App() {
  const [types, setTypes] = useState<IncidentType[]>([]);
  const [typesError, setTypesError] = useState("");

  // Form state (initialised from draft)
  const [draft, setDraft] = useState<Draft>(() => loadDraft());

  const [incident, setIncident] = useState<Incident | null>(null);
  const [coords, setCoords] = useState<Coords | null>(null);
  const [geoStatus, setGeoStatus] = useState<"idle" | "loading" | "ok" | "error">("idle");

  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState<Topic[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState<Connection>("connecting");

  const voice = useVoiceAssistant((action, value) => {
    if (action === "report" && value) {
      setDraft((d) => ({ ...d, selectedType: value }));
    }
    if (action === "first_aid") {
      document.getElementById("question")?.focus();
    }
  });

  /* ---------- Persist draft on every change ---------- */
  useEffect(() => {
    if (incident) return; // don't persist once submitted
    try {
      localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
    } catch {
      /* quota exceeded — ignore */
    }
  }, [draft, incident]);

  /* ---------- Load incident types ---------- */
  useEffect(() => {
    let cancelled = false;
    api<IncidentType[]>("/api/v1/incident-types")
      .then((data) => {
        if (!cancelled) setTypes(data);
      })
      .catch(() => {
        if (!cancelled) setTypesError("Ajali Alert is unavailable. Check your connection and retry.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /* ---------- Restore saved incident ---------- */
  useEffect(() => {
    const id = localStorage.getItem(INCIDENT_ID_KEY);
    if (!id) return;
    api<Incident>(`/api/v1/incidents/${id}`)
      .then(setIncident)
      .catch(() => localStorage.removeItem(INCIDENT_ID_KEY));
  }, []);

  /* ---------- WebSocket with exponential backoff ---------- */
  useEffect(() => {
    if (!incident) return;

    let socket: WebSocket | undefined;
    let retryTimer: number | undefined;
    let backoff = WS_BASE_BACKOFF_MS;
    let closedByUs = false;

    const connect = () => {
      setConnection("connecting");
      try {
        socket = new WebSocket(socketUrl());
      } catch {
        scheduleReconnect();
        return;
      }

      socket.onopen = () => {
        backoff = WS_BASE_BACKOFF_MS;
        setConnection("live");
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message?.data?.id === incident.id) {
            api<Incident>(`/api/v1/incidents/${incident.id}`)
              .then(setIncident)
              .catch(() => undefined);
          }
        } catch {
          /* ignore malformed frames */
        }
      };

      socket.onerror = () => {
        try {
          socket?.close();
        } catch {
          /* ignore */
        }
      };

      socket.onclose = () => {
        if (closedByUs) return;
        setConnection("offline");
        scheduleReconnect();
      };
    };

    const scheduleReconnect = () => {
      if (retryTimer) window.clearTimeout(retryTimer);
      retryTimer = window.setTimeout(() => {
        backoff = Math.min(backoff * 2, WS_MAX_BACKOFF_MS);
        connect();
      }, backoff);
    };

    connect();

    return () => {
      closedByUs = true;
      if (retryTimer) window.clearTimeout(retryTimer);
      try {
        socket?.close();
      } catch {
        /* ignore */
      }
    };
  }, [incident?.id]);

  /* ---------- Handlers ---------- */

  const locate = useCallback(() => {
    if (!navigator.geolocation) {
      setError("GPS is not supported. Enter a location description instead.");
      setGeoStatus("error");
      return;
    }
    setGeoStatus("loading");
    setError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          accuracy: position.coords.accuracy,
        });
        setGeoStatus("ok");
      },
      () => {
        setGeoStatus("error");
        setError("GPS permission was unavailable. Enter a location description instead.");
      },
      { enableHighAccuracy: true, timeout: 10_000, maximumAge: 0 },
    );
  }, []);

  // Auto-attempt geolocation on mount
  useEffect(() => {
    if (!incident && geoStatus === "idle" && navigator.geolocation) {
      locate();
    }
  }, [incident, geoStatus, locate]);

  const submit = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      setError("");

      const desc = draft.description.trim();
      const loc = draft.location.trim();

      if (!draft.selectedType) {
        setError("Choose an emergency type.");
        return;
      }
      if (!coords && loc.length < 3) {
        setError("Enable GPS or describe your location.");
        return;
      }
      if (desc.length < 5) {
        setError("Describe what happened (at least a few words).");
        return;
      }

      setBusy(true);
      try {
        const payload = {
          type_code: draft.selectedType,
          description: desc,
          casualty_count: Math.max(0, Number(draft.casualties) || 0),
          latitude: coords?.lat ?? DEFAULT_COORDS.lat,
          longitude: coords?.lng ?? DEFAULT_COORDS.lng,
          location_description: loc,
          landmark: draft.landmark.trim(),
        };
        const result = await api<Incident>("/api/v1/incidents", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        setIncident(result);
        localStorage.setItem(INCIDENT_ID_KEY, result.id);
        localStorage.removeItem(DRAFT_KEY);
      } catch (requestError) {
        setError(requestError instanceof Error ? requestError.message : "Unable to submit the emergency.");
      } finally {
        setBusy(false);
      }
    },
    [coords, draft],
  );

  const askFirstAid = useCallback(async () => {
    const q = question.trim();
    if (q.length < 2) return;
    setBusy(true);
    try {
      const results = await api<Topic[]>("/api/v1/first-aid/ask", {
        method: "POST",
        body: JSON.stringify({ query: q, incident_id: incident?.id }),
      });
      setAnswers(results);
    } catch {
      setError("First-aid guidance is temporarily unavailable.");
    } finally {
      setBusy(false);
    }
  }, [question, incident?.id]);

  const reset = useCallback(() => {
    localStorage.removeItem(INCIDENT_ID_KEY);
    localStorage.removeItem(DRAFT_KEY);
    setIncident(null);
    setDraft(EMPTY_DRAFT);
    setCoords(null);
    setGeoStatus("idle");
    setError("");
    setQuestion("");
    setAnswers([]);
  }, []);

  const cancelIncident = useCallback(async () => {
    if (!incident) return;
    if (!confirm("Cancel this incident? Responders will be stood down.")) return;
    setBusy(true);
    try {
      await api(`/api/v1/incidents/${incident.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: "CANCELLED", note: "Cancelled by reporter" }),
      });
      reset();
    } catch {
      setError("Could not cancel. Try again or call the emergency line.");
    } finally {
      setBusy(false);
    }
  }, [incident, reset]);

  const shareIncident = useCallback(async () => {
    if (!incident) return;
    const text = `Ajali Alert — Case ${incident.incident_number}\nStatus: ${incident.status}\nLocation: ${incident.location_description || "GPS shared"}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: "Ajali Alert incident", text });
        return;
      } catch {
        /* user cancelled */
      }
    }
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      /* ignore */
    }
  }, [incident]);

  /* ---------- Derived ---------- */

  const gpsLabel = useMemo(() => {
    if (geoStatus === "loading") return "Getting your location…";
    if (!coords) return "Location helps responders find you";
    const acc = coords.accuracy ? ` (±${Math.round(coords.accuracy)}m)` : "";
    return `GPS captured: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}${acc}`;
  }, [coords, geoStatus]);

  const canSubmit = useMemo(() => {
    return (
      draft.selectedType &&
      (coords || draft.location.trim().length >= 3) &&
      draft.description.trim().length >= 5 &&
      !busy
    );
  }, [draft, coords, busy]);

  /* ---------- Render ---------- */

  return (
    <div className="shell">
      <header className="top">
        <div className="brand">
          <div className="mark">AL</div>
          <div>
            <div className="word">Ajali Alert</div>
            <div className="sub">Emergency response service</div>
          </div>
        </div>
        <div className="top-actions">
          {incident && <ConnectionBadge state={connection} />}
          <button
            className="voice"
            type="button"
            onClick={voice.state === "listening" ? voice.stop : voice.start}
            disabled={!voice.supported}
            aria-label={voice.state === "listening" ? "Stop listening" : "Talk to Ajali"}
            title={voice.supported ? "Talk to Ajali" : "Voice input unavailable"}
          >
            {voice.state === "listening" ? <MicOff size={16} /> : <Mic size={16} />}
          </button>
        </div>
      </header>

      {(voice.transcript || voice.response || voice.state === "unsupported") && (
        <div className="voice-panel" aria-live="polite">
          <strong>
            {voice.state === "listening"
              ? "Listening"
              : voice.state === "speaking"
                ? "Ajali Intelligence"
                : "Voice assistant"}
          </strong>
          {voice.transcript && <span>You said: {voice.transcript}</span>}
          {voice.response && <span>{voice.response}</span>}
          {voice.state === "unsupported" && (
            <span>Voice input is unavailable in this browser. Use the emergency form.</span>
          )}
        </div>
      )}

      {!incident ? (
        /* ============================================================ */
        /* REPORTING FORM                                               */
        /* ============================================================ */
        <main>
          <section className="hero">
            <div className="eyebrow">One-tap emergency reporting</div>
            <h1 className="title">Help is closer when we know where.</h1>
            <p className="lede">
              Share what is happening and your location. Ajali Alert routes the report to the
              appropriate response team.
            </p>
          </section>

          <form onSubmit={submit} className="section">
            <h2>What is happening?</h2>

            {typesError && (
              <div className="error" role="alert">
                {typesError}
              </div>
            )}

            {!types.length && !typesError && (
              <p className="muted">Loading emergency types…</p>
            )}

            <div className="types">
              {types.map((type) => (
                <button
                  type="button"
                  className={`type ${draft.selectedType === type.code ? "selected" : ""}`}
                  key={type.code}
                  onClick={() => setDraft((d) => ({ ...d, selectedType: type.code }))}
                  aria-pressed={draft.selectedType === type.code}
                >
                  <Siren size={20} />
                  <strong>{type.name}</strong>
                  <small>
                    {type.code === "medical"
                      ? "Injury or medical emergency"
                      : `Request ${type.name.toLowerCase()} support`}
                  </small>
                </button>
              ))}
            </div>

            <div className="form section">
              <label htmlFor="description">Describe the emergency</label>
              <textarea
                id="description"
                rows={4}
                value={draft.description}
                onChange={(e) => setDraft((d) => ({ ...d, description: e.target.value }))}
                placeholder="What happened? Mention injuries, hazards, or immediate danger."
                required
              />

              <div className="grid">
                <div>
                  <label htmlFor="casualties">Casualties</label>
                  <input
                    id="casualties"
                    type="number"
                    min="0"
                    value={draft.casualties}
                    onChange={(e) =>
                      setDraft((d) => ({
                        ...d,
                        casualties: Math.max(0, Number(e.target.value) || 0),
                      }))
                    }
                  />
                </div>
                <div>
                  <label htmlFor="landmark">Landmark</label>
                  <input
                    id="landmark"
                    value={draft.landmark}
                    onChange={(e) => setDraft((d) => ({ ...d, landmark: e.target.value }))}
                    placeholder="Optional"
                  />
                </div>
              </div>

              <label htmlFor="location">Location description</label>
              <input
                id="location"
                value={draft.location}
                onChange={(e) => setDraft((d) => ({ ...d, location: e.target.value }))}
                placeholder="Street, building, or nearby landmark"
              />

              <div className={`location ${coords ? "ok" : geoStatus === "error" ? "err" : ""}`}>
                <span>
                  <MapPin size={15} /> {gpsLabel}
                </span>
                <button
                  type="button"
                  onClick={locate}
                  disabled={geoStatus === "loading"}
                >
                  <RefreshCw size={14} /> {coords ? "Update" : "Use GPS"}
                </button>
              </div>

              {error && (
                <div className="error" role="alert">
                  {error}
                </div>
              )}

              <button className="primary" disabled={!canSubmit}>
                {busy ? "Sending report…" : "Report emergency"}
              </button>
            </div>
          </form>

          <p className="footer">
            If you are in immediate danger, move somewhere safer if possible. This service does not
            replace your local emergency phone line.
          </p>
        </main>
      ) : (
        /* ============================================================ */
        /* ACTIVE INCIDENT                                              */
        /* ============================================================ */
        <main>
          <section className="hero">
            <div className="eyebrow">Active incident</div>
            <h1 className="title">Your report is moving.</h1>
            <p className="lede">Keep this page open for updates from the response network.</p>
          </section>

          <section className="card">
            <div className="muted incident-id-row">
              <span>{incident.incident_number}</span>
              <CopyButton text={incident.incident_number} label="Copy case" />
            </div>
            <h2>{incident.type?.name ?? "Emergency report"}</h2>
            <span className="status">{incident.status.replaceAll("_", " ")}</span>

            <div className="meta">
              <span>Priority</span>
              <b>Level {incident.priority}</b>
            </div>
            <div className="meta">
              <span>Location</span>
              <b>{incident.location_description || "GPS location shared"}</b>
            </div>
            <div className="meta">
              <span>Casualties</span>
              <b>{incident.casualty_count}</b>
            </div>
          </section>

          <section className="card">
            <h2>
              <Activity size={18} /> Timeline
            </h2>
            <Timeline incident={incident} />
          </section>

          <section className="card">
            <h2>
              <Cross size={18} /> First aid while you wait
            </h2>
            <TopicList topics={incident.first_aid_suggestions} />

            <label htmlFor="question">Ask for specific guidance</label>
            <input
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. bleeding from a leg wound"
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  askFirstAid();
                }
              }}
            />
            <button
              className="primary"
              style={{ marginTop: 10 }}
              onClick={askFirstAid}
              disabled={busy || question.trim().length < 2}
            >
              Ask Ajali guidance
            </button>
            <TopicList topics={answers} />
          </section>

          {error && (
            <div className="error" role="alert">
              {error}
            </div>
          )}

          <div className="incident-actions">
            <button className="primary" onClick={shareIncident} type="button">
              <Share2 size={16} /> Share case
            </button>
            <a className="primary ghost-link" href="tel:999" aria-label="Call 999">
              <Phone size={16} /> Call 999
            </a>
            <button
              className="primary danger"
              onClick={cancelIncident}
              disabled={busy || ["RESOLVED", "CLOSED", "CANCELLED"].includes(incident.status)}
              type="button"
            >
              <X size={16} /> Cancel incident
            </button>
          </div>

          <button
            className="primary"
            style={{ marginTop: 18, background: "transparent", border: "1px solid var(--line)" }}
            onClick={reset}
            type="button"
          >
            <ShieldAlert size={16} /> Report another emergency
          </button>
        </main>
      )}
    </div>
  );
}
