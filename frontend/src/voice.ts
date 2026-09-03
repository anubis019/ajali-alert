import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api";

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

type RecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  }
}

export type VoiceState = "idle" | "listening" | "speaking" | "unsupported" | "error";

function getRecognition(): RecognitionConstructor | undefined {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

function localResponse(text: string): string {
  const normalized = text.toLowerCase();
  if (normalized.includes("fire") || normalized.includes("moto")) return "For fire, move away from smoke and heat, evacuate if safe, and contact emergency services.";
  if (normalized.includes("bleed") || normalized.includes("damu")) return "For serious bleeding, apply firm direct pressure with clean material and wait for professional responders.";
  if (normalized.includes("unconscious") || normalized.includes("breathing")) return "Check whether the person is breathing, call emergency services, and follow the operator's instructions.";
  if (normalized.includes("first aid") || normalized.includes("msaada wa kwanza")) return "Tell me the injury or situation and I will look up approved first-aid guidance.";
  return "I can help you report an emergency or provide approved first-aid guidance. Say fire, bleeding, or first aid.";
}

export function useVoiceAssistant(onAction?: (action: "report" | "first_aid", value?: string) => void) {
  const [state, setState] = useState<VoiceState>(() => (getRecognition() ? "idle" : "unsupported"));
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const recognitionRef = useRef<SpeechRecognitionLike | undefined>(undefined);

  const speak = useCallback((text: string) => {
    setResponse(text);
    if (!window.speechSynthesis) { setState("idle"); return; }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = 0.92;
    utterance.onstart = () => setState("speaking");
    utterance.onend = () => setState("idle");
    utterance.onerror = () => setState("error");
    window.speechSynthesis.speak(utterance);
  }, []);

  const process = useCallback(async (text: string) => {
    const normalized = text.toLowerCase();
    setTranscript(text);
    if (normalized.includes("report") || normalized.includes("emergency") || normalized.includes("help") || normalized.includes("dharura")) {
      const type = normalized.includes("fire") || normalized.includes("moto") ? "fire" : normalized.includes("medical") ? "medical" : normalized.includes("police") ? "security" : normalized.includes("accident") || normalized.includes("ajali") ? "road_accident" : undefined;
      onAction?.("report", type);
      speak(type ? `Opening a ${type.replace("_", " ")} emergency report.` : "Opening an emergency report. Choose the emergency type.");
      return;
    }
    if (normalized.includes("first aid") || normalized.includes("msaada wa kwanza")) {
      onAction?.("first_aid");
    }
    const token = localStorage.getItem("access_token");
    if (token) {
      try {
        const result = await api<{ reply: string }>("/api/v1/assistant/chat", { method: "POST", body: JSON.stringify({ message: text, user_role: "citizen" }) });
        speak(result.reply);
        return;
      } catch { /* use the deterministic safety response below */ }
    }
    speak(localResponse(text));
  }, [onAction, speak]);

  const start = useCallback(() => {
    const Constructor = getRecognition();
    if (!Constructor) { setState("unsupported"); return; }
    const recognition = new Constructor();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => { const result = event.results[event.resultIndex]; if (result?.isFinal) void process(result[0].transcript.trim()); };
    recognition.onerror = () => setState("error");
    recognition.onend = () => setState((current) => current === "listening" ? "idle" : current);
    recognitionRef.current = recognition;
    setTranscript("");
    setState("listening");
    recognition.start();
  }, [process]);

  const stop = useCallback(() => { recognitionRef.current?.stop(); window.speechSynthesis?.cancel(); setState("idle"); }, []);
  useEffect(() => () => { recognitionRef.current?.stop(); window.speechSynthesis?.cancel(); }, []);
  return { state, transcript, response, start, stop, supported: state !== "unsupported" };
}
