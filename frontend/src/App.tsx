import { FormEvent, useEffect, useState } from "react";
import { Activity, Cross, MapPin, Mic, MicOff, RefreshCw, ShieldAlert, Siren } from "lucide-react";
import { api, Incident, IncidentType, socketUrl, Topic } from "./api";
import { useVoiceAssistant } from "./voice";

const savedId = () => localStorage.getItem("ajali_incident_id");

function Topics({ topics }: { topics: Topic[] }) {
  if (!topics.length) return <p className="muted">No matching guidance. Add detail or ask a specific question.</p>;
  return <div>{topics.map((topic) => <details className="topic" key={topic.id}><summary>{topic.title}</summary><ol>{topic.steps.map((step) => <li key={step}>{step}</li>)}</ol>{topic.warnings.map((warning) => <p className="muted" key={warning}>Warning: {warning}</p>)}</details>)}</div>;
}

export function App() {
  const [types, setTypes] = useState<IncidentType[]>([]);
  const [selectedType, setSelectedType] = useState("");
  const [incident, setIncident] = useState<Incident | null>(null);
  const [coords, setCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [casualties, setCasualties] = useState(0);
  const [landmark, setLandmark] = useState("");
  const [question, setQuestion] = useState("");
  const [answers, setAnswers] = useState<Topic[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [connection, setConnection] = useState("connecting");
  const voice = useVoiceAssistant((action, value) => {
    if (action === "report" && value) setSelectedType(value);
    if (action === "first_aid") document.getElementById("question")?.focus();
  });

  useEffect(() => { api<IncidentType[]>("/api/v1/incident-types").then(setTypes).catch(() => setError("Ajali Alert is unavailable. Check your connection and retry.")); }, []);
  useEffect(() => {
    const id = savedId(); if (!id) return;
    api<Incident>(`/api/v1/incidents/${id}`).then(setIncident).catch(() => localStorage.removeItem("ajali_incident_id"));
  }, []);
  useEffect(() => {
    if (!incident) return;
    let socket: WebSocket | undefined; let retry: number;
    const connect = () => { socket = new WebSocket(socketUrl()); socket.onopen = () => setConnection("live"); socket.onclose = () => { setConnection("offline"); retry = window.setTimeout(connect, 4000); }; socket.onerror = () => socket?.close(); socket.onmessage = (event) => { const message = JSON.parse(event.data); if (message.data?.id === incident.id) api<Incident>(`/api/v1/incidents/${incident.id}`).then(setIncident).catch(() => undefined); }; };
    connect(); return () => { window.clearTimeout(retry); socket?.close(); };
  }, [incident?.id]);

  function locate() {
    if (!navigator.geolocation) { setError("GPS is not supported. Enter a location description instead."); return; }
    navigator.geolocation.getCurrentPosition((position) => setCoords({ lat: position.coords.latitude, lng: position.coords.longitude }), () => setError("GPS permission was unavailable. Enter a location description instead."), { enableHighAccuracy: true, timeout: 8000 });
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError("");
    if (!selectedType || (!coords && location.trim().length < 3) || description.trim().length < 5) { setError("Choose an emergency type, describe what happened, and provide a location."); return; }
    setBusy(true);
    try { const result = await api<Incident>("/api/v1/incidents", { method: "POST", body: JSON.stringify({ type_code: selectedType, description: description.trim(), casualty_count: casualties, latitude: coords?.lat ?? -1.286389, longitude: coords?.lng ?? 36.817223, location_description: location.trim(), landmark: landmark.trim() }) }); setIncident(result); localStorage.setItem("ajali_incident_id", result.id); } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "Unable to submit the emergency."); } finally { setBusy(false); }
  }
  async function askFirstAid() { if (question.trim().length < 2) return; setBusy(true); try { setAnswers(await api<Topic[]>("/api/v1/first-aid/ask", { method: "POST", body: JSON.stringify({ query: question.trim(), incident_id: incident?.id }) })); } catch { setError("First-aid guidance is temporarily unavailable."); } finally { setBusy(false); } }
  function reset() { localStorage.removeItem("ajali_incident_id"); setIncident(null); setSelectedType(""); setDescription(""); setCasualties(0); setLocation(""); setLandmark(""); setError(""); }

  return <div className="shell">
    <header className="top"><div className="brand"><div className="mark">AL</div><div><div className="word">Ajali Alert</div><div className="sub">Emergency response service</div></div></div><div className="top-actions"><div className="live"><span className="dot" />{connection}</div><button className="voice" type="button" onClick={voice.state === "listening" ? voice.stop : voice.start} disabled={!voice.supported} aria-label={voice.state === "listening" ? "Stop listening" : "Talk to Ajali"} title={voice.supported ? "Talk to Ajali" : "Voice input unavailable"}>{voice.state === "listening" ? <MicOff size={16} /> : <Mic size={16} />}</button></div></header>
    {(voice.transcript || voice.response || voice.state === "unsupported") && <div className="voice-panel" aria-live="polite"><strong>{voice.state === "listening" ? "Listening" : voice.state === "speaking" ? "Ajali Intelligence" : "Voice assistant"}</strong>{voice.transcript && <span>You said: {voice.transcript}</span>}{voice.response && <span>{voice.response}</span>}{voice.state === "unsupported" && <span>Voice input is unavailable in this browser. Use the emergency form.</span>}</div>}
    {!incident ? <main><section className="hero"><div className="eyebrow">One-tap emergency reporting</div><h1 className="title">Help is closer when we know where.</h1><p className="lede">Share what is happening and your location. Ajali Alert routes the report to the appropriate response team.</p></section>
      <form onSubmit={submit} className="section"><h2>What is happening?</h2><div className="types">{types.map((type) => <button type="button" className={`type ${selectedType === type.code ? "selected" : ""}`} key={type.code} onClick={() => setSelectedType(type.code)}><Siren size={20} /><strong>{type.name}</strong><small>{type.code === "medical" ? "Injury or medical emergency" : `Request ${type.name.toLowerCase()} support`}</small></button>)}</div>
        <div className="form section"><label htmlFor="description">Describe the emergency</label><textarea id="description" rows={4} value={description} onChange={(event) => setDescription(event.target.value)} placeholder="What happened? Mention injuries, hazards, or immediate danger." /><div className="grid"><div><label htmlFor="casualties">Casualties</label><input id="casualties" type="number" min="0" value={casualties} onChange={(event) => setCasualties(Math.max(0, Number(event.target.value)))} /></div><div><label htmlFor="landmark">Landmark</label><input id="landmark" value={landmark} onChange={(event) => setLandmark(event.target.value)} placeholder="Optional" /></div></div><label htmlFor="location">Location description</label><input id="location" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Street, building, or nearby landmark" /><div className={`location ${coords ? "ok" : ""}`}><span><MapPin size={15} /> {coords ? `GPS captured: ${coords.lat.toFixed(4)}, ${coords.lng.toFixed(4)}` : "Location helps responders find you"}</span><button type="button" onClick={locate}><RefreshCw size={14} /> {coords ? "Update" : "Use GPS"}</button></div>{error && <div className="error" role="alert">{error}</div>}<button className="primary" disabled={busy}>{busy ? "Sending report..." : "Report emergency"}</button></div>
      </form><p className="footer">If you are in immediate danger, move somewhere safer if possible. This service does not replace your local emergency phone line.</p></main>
      : <main><section className="hero"><div className="eyebrow">Active incident</div><h1 className="title">Your report is moving.</h1><p className="lede">Keep this page open for updates from the response network.</p></section><section className="card"><div className="muted">{incident.incident_number}</div><h2>{incident.type?.name ?? "Emergency report"}</h2><span className="status">{incident.status.replaceAll("_", " ")}</span><div className="meta"><span>Priority</span><b>Level {incident.priority}</b></div><div className="meta"><span>Location</span><b>{incident.location_description || "GPS location shared"}</b></div><div className="meta"><span>Casualties</span><b>{incident.casualty_count}</b></div></section><section className="card"><h2><Activity size={18} /> Timeline</h2><ul className="timeline">{incident.history.slice().reverse().map((event) => <li key={`${event.status}-${event.created_at}`}><strong>{event.status.replaceAll("_", " ")}</strong><small>{event.note} · {new Date(event.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></li>)}</ul></section><section className="card"><h2><Cross size={18} /> First aid while you wait</h2><Topics topics={incident.first_aid_suggestions} /><label htmlFor="question">Ask for specific guidance</label><input id="question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="e.g. bleeding from a leg wound" /><button className="primary" style={{ marginTop: 10 }} onClick={askFirstAid} disabled={busy}>Ask Ajali guidance</button><Topics topics={answers} /></section>{error && <div className="error" role="alert">{error}</div>}<button className="primary" style={{ marginTop: 18, background: "transparent", border: "1px solid var(--line)" }} onClick={reset}><ShieldAlert size={16} /> Report another emergency</button></main>}
  </div>;
}
