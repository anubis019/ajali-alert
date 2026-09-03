export type IncidentType = { code: string; name: string; icon: string };
export type Topic = { id: string; title: string; steps: string[]; warnings: string[] };
export type Incident = {
  id: string; incident_number: string; status: string; priority: number; casualty_count: number;
  description: string; latitude: number; longitude: number; location_description: string;
  landmark: string; created_at: string; updated_at: string; type?: IncidentType;
  history: { status: string; note: string; created_at: string }[];
  assignments: { eta_minutes: number; status: string; responder: { name: string; responder_type: string } }[];
  first_aid_suggestions: Topic[];
};

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, { ...options, headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) } });
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? "Ajali Alert could not complete that request."); }
  return response.json() as Promise<T>;
}
export const socketUrl = () => `${API.replace(/^http/, "ws")}/ws`;
