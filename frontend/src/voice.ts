import { useCallback, useEffect, useRef, useState } from "react";
import { auth, http } from "./api";

/* ==================================================================
   Web Speech API types
   ================================================================== */

type SpeechRecognitionResultAlternative = {
  transcript: string;
  confidence: number;
};

type SpeechRecognitionResult = {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionResultAlternative;
};

type SpeechRecognitionResultList = {
  length: number;
  [index: number]: SpeechRecognitionResult;
};

type SpeechRecognitionEvent = {
  resultIndex: number;
  results: SpeechRecognitionResultList;
};

type SpeechRecognitionErrorEvent = {
  error: string;
  message?: string;
};

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  maxAlternatives: number;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type RecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  }
}

/* ==================================================================
   Public types
   ================================================================== */

export type VoiceState =
  | "idle"
  | "listening"
  | "thinking"
  | "speaking"
  | "unsupported"
  | "error";

export type VoiceAction = "report" | "first_aid";

export interface UseVoiceAssistant {
  state: VoiceState;
  transcript: string;
  response: string;
  error: string;
  supported: boolean;
  start: () => void;
  stop: () => void;
  cancel: () => void;
}

/* ==================================================================
   Config
   ================================================================== */

const LISTEN_TIMEOUT_MS = 12_000;
const MAX_TRANSCRIPT_LENGTH = 500;
const RECOGNITION_LANG = "en-KE"; // fall back to en-US if unsupported
const RECOGNITION_LANG_FALLBACK = "en-US";

/* ==================================================================
   Helpers
   ================================================================== */

function getRecognition(): RecognitionConstructor | undefined {
  return window.SpeechRecognition ?? window.webkitSpeechRecognition;
}

function getSynth(): SpeechSynthesis | undefined {
  return typeof window !== "undefined" ? window.speechSynthesis : undefined;
}

/** Trim, collapse whitespace, cap length. */
function clean(text: string): string {
  return text.replace(/\s+/g, " ").trim().slice(0, MAX_TRANSCRIPT_LENGTH);
}

/** Deterministic first-aid fallback. Bilingual (EN + basic SW). */
function localResponse(text: string): string {
  const t = text.toLowerCase();

  if (/(fire|moto|burn|smoke|moshi)/.test(t)) {
    return "For fire, move away from smoke and heat, evacuate if safe, and call emergency services.";
  }
  if (/(bleed|damu|wound|jeraha)/.test(t)) {
    return "For serious bleeding, apply firm direct pressure with clean material and wait for professional responders.";
  }
  if (/(unconscious|breathing|kupumua|amezimia)/.test(t)) {
    return "Check whether the person is breathing, call emergency services, and follow the operator's instructions.";
  }
  if (/(accident|crash|collision|ajali)/.test(t)) {
    return "For a road accident, secure the scene if safe, warn oncoming traffic, and wait for responders.";
  }
  if (/(first aid|msaada wa kwanza)/.test(t)) {
    return "Tell me the injury or situation and I will look up approved first-aid guidance.";
  }
  return "I can help you report an emergency or provide approved first-aid guidance. Say fire, bleeding, or first aid.";
}

/** Map spoken words to an incident type code. */
function detectIncidentType(text: string): string | undefined {
  const t = text.toLowerCase();
  if (/(fire|moto|burn|smoke)/.test(t)) return "fire";
  if (/(medical|injury|bleed|damu|ambulance)/.test(t)) return "medical";
  if (/(police|security|theft|robbery)/.test(t)) return "security";
  if (/(accident|crash|collision|ajali)/.test(t)) return "road_accident";
  return undefined;
}

/* ==================================================================
   Hook
   ================================================================== */

export function useVoiceAssistant(
  onAction?: (action: VoiceAction, value?: string) => void,
): UseVoiceAssistant {
  const [state, setState] = useState<VoiceState>(() =>
    getRecognition() ? "idle" : "unsupported",
  );
  const [transcript, setTranscript] = useState("");
  const [response, setResponse] = useState("");
  const [error, setError] = useState("");

  const recognitionRef = useRef<SpeechRecognitionLike | undefined>(undefined);
  const listenTimeoutRef = useRef<number | undefined>(undefined);
  const speakTimeoutRef = useRef<number | undefined>(undefined);
  const mountedRef = useRef(true);

  /* -------------------------------------------------------------- */
  /* Cleanup on unmount                                             */
  /* -------------------------------------------------------------- */
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (listenTimeoutRef.current) window.clearTimeout(listenTimeoutRef.current);
      if (speakTimeoutRef.current) window.clearTimeout(speakTimeoutRef.current);
      try {
        recognitionRef.current?.abort();
      } catch {
        /* ignore */
      }
      getSynth()?.cancel();
    };
  }, []);

  /* -------------------------------------------------------------- */
  /* Speak                                                          */
  /* -------------------------------------------------------------- */
  const speak = useCallback((text: string) => {
    if (!mountedRef.current) return;
    setResponse(text);

    const synth = getSynth();
    if (!synth) {
      setState("idle");
      return;
    }

    // Cancel any in-flight speech
    synth.cancel();
    if (speakTimeoutRef.current) window.clearTimeout(speakTimeoutRef.current);

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = RECOGNITION_LANG;
    utterance.rate = 0.92;
    utterance.pitch = 1;

    utterance.onstart = () => {
      if (mountedRef.current) setState("speaking");
    };
    utterance.onend = () => {
      if (speakTimeoutRef.current) window.clearTimeout(speakTimeoutRef.current);
      if (mountedRef.current) setState("idle");
    };
    utterance.onerror = (event) => {
      if (speakTimeoutRef.current) window.clearTimeout(speakTimeoutRef.current);
      // "interrupted" and "canceled" are normal when we cancel speech
      if (event.error === "interrupted" || event.error === "canceled") return;
      if (mountedRef.current) {
        setError("Voice playback failed.");
        setState("idle");
      }
    };

    // Hard timeout in case onend never fires (some browsers)
    speakTimeoutRef.current = window.setTimeout(() => {
      if (mountedRef.current) setState("idle");
    }, 15_000);

    synth.speak(utterance);
  }, []);

  /* -------------------------------------------------------------- */
  /* Process recognised text                                        */
  /* -------------------------------------------------------------- */
  const process = useCallback(
    async (rawText: string) => {
      const text = clean(rawText);
      if (!text) {
        setState("idle");
        return;
      }

      setTranscript(text);
      setError("");
      setState("thinking");

      const t = text.toLowerCase();

      /* ---- Report intent ---- */
      if (/(report|emergency|help|dharura|nisaidie)/.test(t)) {
        const type = detectIncidentType(t);
        onAction?.("report", type);
        speak(
          type
            ? `Opening a ${type.replace(/_/g, " ")} emergency report.`
            : "Opening an emergency report. Choose the emergency type.",
        );
        return;
      }

      /* ---- First-aid intent ---- */
      if (/(first aid|msaada wa kwanza)/.test(t)) {
        onAction?.("first_aid");
        // Fall through to try the AI backend for a real answer
      }

      /* ---- Try authenticated AI, fall back to local knowledge ---- */
      if (auth.isLoggedIn()) {
        try {
          const result = await http.post<{ reply: string }>(
            "/api/v1/assistant/chat",
            { message: text, user_role: "citizen" },
          );
          speak(result.reply || localResponse(text));
          return;
        } catch (err) {
          // Silent fallback — do not surface AI errors to the citizen
          console.warn("[voice] AI backend unavailable, using local response", err);
        }
      }

      speak(localResponse(text));
    },
    [onAction, speak],
  );

  /* -------------------------------------------------------------- */
  /* Start listening                                                */
  /* -------------------------------------------------------------- */
  const start = useCallback(() => {
    const Constructor = getRecognition();
    if (!Constructor) {
      setState("unsupported");
      return;
    }

    // Stop anything currently speaking so we don't record our own voice
    getSynth()?.cancel();

    // Stop any previous recognition session
    try {
      recognitionRef.current?.abort();
    } catch {
      /* ignore */
    }

    const recognition = new Constructor();
    // Try en-KE first; if the browser rejects it, use en-US
    try {
      recognition.lang = RECOGNITION_LANG;
    } catch {
      recognition.lang = RECOGNITION_LANG_FALLBACK;
    }
    recognition.interimResults = false;
    recognition.continuous = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      if (mountedRef.current) {
        setTranscript("");
        setError("");
        setState("listening");
      }
    };

    recognition.onresult = (event) => {
      const result = event.results?.[event.resultIndex];
      if (!result?.isFinal) return;
      const text = result[0]?.transcript ?? "";
      if (text) void process(text);
    };

    recognition.onerror = (event) => {
      if (!mountedRef.current) return;
      if (listenTimeoutRef.current) window.clearTimeout(listenTimeoutRef.current);

      // Some errors are user-driven and should be silent
      const silent = new Set(["aborted", "no-speech"]);
      if (silent.has(event.error)) {
        setState("idle");
        return;
      }

      const messages: Record<string, string> = {
        "not-allowed": "Microphone access was denied.",
        "service-not-allowed": "Microphone access was denied.",
        "audio-capture": "No microphone was found.",
        network: "Voice recognition needs a network connection.",
      };
      setError(messages[event.error] ?? "Voice input failed. Try again.");
      setState("error");
    };

    recognition.onend = () => {
      if (listenTimeoutRef.current) window.clearTimeout(listenTimeoutRef.current);
      if (mountedRef.current) {
        setState((current) => (current === "listening" ? "idle" : current));
      }
    };

    recognitionRef.current = recognition;

    // Hard timeout in case the browser never fires onresult
    listenTimeoutRef.current = window.setTimeout(() => {
      try {
        recognition.stop();
      } catch {
        /* ignore */
      }
      if (mountedRef.current) {
        setError("No speech detected. Try again.");
        setState("idle");
      }
    }, LISTEN_TIMEOUT_MS);

    try {
      recognition.start();
    } catch {
      if (listenTimeoutRef.current) window.clearTimeout(listenTimeoutRef.current);
      setError("Could not start voice input.");
      setState("error");
    }
  }, [process]);

  /* -------------------------------------------------------------- */
  /* Stop / cancel                                                  */
  /* -------------------------------------------------------------- */
  const stop = useCallback(() => {
    if (listenTimeoutRef.current) window.clearTimeout(listenTimeoutRef.current);
    try {
      recognitionRef.current?.stop();
    } catch {
      /* ignore */
    }
    getSynth()?.cancel();
    if (mountedRef.current) setState("idle");
  }, []);

  const cancel = useCallback(() => {
    if (listenTimeoutRef.current) window.clearTimeout(listenTimeoutRef.current);
    if (speakTimeoutRef.current) window.clearTimeout(speakTimeoutRef.current);
    try {
      recognitionRef.current?.abort();
    } catch {
      /* ignore */
    }
    getSynth()?.cancel();
    if (mountedRef.current) {
      setTranscript("");
      setResponse("");
      setError("");
      setState("idle");
    }
  }, []);

  return {
    state,
    transcript,
    response,
    error,
    supported: state !== "unsupported",
    start,
    stop,
    cancel,
  };
}
