import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import AppLayout from "../components/layout/AppLayout";
import Icon from "../components/ui/Icon";
import api from "../api/axios";
import { getVehicles, type Vehicle } from "../api/vehicles";

interface DiagnosisResult {
  vehicle_id: number;
  diagnosis: string;
  possible_causes: string[];
  recommended_service: string;
  priority: string;
  confidence: number;
  advice: string;
}

interface SpeechRecognitionEventLike extends Event {
  results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEventLike extends Event {
  error: string;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: (() => void) | null;
  onend: (() => void) | null;
  onerror: ((event: SpeechRecognitionErrorEventLike) => void) | null;
  onresult: ((event: SpeechRecognitionEventLike) => void) | null;
}

type SpeechRecognitionConstructor = new () => SpeechRecognitionLike;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

const exampleProblems = [
  "My car is making a grinding noise when I press the brakes.",
  "My car engine is overheating and there is smoke coming from the engine.",
  "My car will not start and I only hear clicking when I turn the key.",
  "My tyre is completely flat and I cannot drive.",
];

function getPriorityClass(priority: string) {
  const normalized = priority.trim().toLowerCase();
  if (normalized === "critical") return "critical";
  if (normalized === "high") return "high";
  if (normalized === "medium") return "medium";
  return "low";
}

function formatService(service: string) {
  if (!service) return "Roadside assistance";
  return service
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getPriorityColors(priority: string) {
  const kind = getPriorityClass(priority);
  if (kind === "critical") return { background: "var(--color-emergency-soft)", color: "var(--color-emergency-text)" };
  if (kind === "high") return { background: "var(--color-warning-soft)", color: "var(--color-warning-text)" };
  if (kind === "medium") return { background: "var(--color-warning-soft)", color: "var(--color-warning-text)" };
  return { background: "var(--color-success-soft)", color: "var(--color-success)" };
}

export default function AIDiagnosis() {
  const navigate = useNavigate();
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);
  const transcriptBeforeListeningRef = useRef("");

  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [selectedVehicleId, setSelectedVehicleId] = useState<number | "">("");
  const [symptoms, setSymptoms] = useState("");
  const [result, setResult] = useState<DiagnosisResult | null>(null);
  const [vehiclesLoading, setVehiclesLoading] = useState(true);
  const [diagnosing, setDiagnosing] = useState(false);
  const [listening, setListening] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(true);
  const [voiceError, setVoiceError] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognitionAPI) {
      setVoiceSupported(false);
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = "en-IN";

    recognition.onstart = () => {
      setListening(true);
      setVoiceError("");
    };

    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";

      for (let i = event.results.length - 1; i >= 0; i -= 1) {
        const resultItem = event.results[i];
        const transcript = resultItem[0]?.transcript ?? "";
        if (resultItem.isFinal) {
          finalText = `${transcript} ${finalText}`.trim();
        } else {
          interimText = `${transcript} ${interimText}`.trim();
        }
      }

      const base = transcriptBeforeListeningRef.current.trim();
      const spokenText = `${finalText} ${interimText}`.trim();
      const combined = [base, spokenText].filter(Boolean).join(" ").trim();
      setSymptoms(combined);
    };

    recognition.onerror = (event) => {
      console.error("Speech recognition error:", event.error);
      setListening(false);

      const messages: Record<string, string> = {
        "not-allowed": "Microphone permission was denied. Allow microphone access in Chrome and try again.",
        "audio-capture": "No microphone was detected. Check your microphone and try again.",
        network: "Speech recognition could not connect. Please try again or type the problem manually.",
        "no-speech": "No speech was detected. Please speak clearly and try again.",
      };

      setVoiceError(messages[event.error] || "Voice input failed. Please try again.");
    };

    recognition.onend = () => {
      setListening(false);
    };

    recognitionRef.current = recognition;

    return () => {
      recognition.abort();
      recognitionRef.current = null;
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    const loadVehicles = async () => {
      try {
        setVehiclesLoading(true);
        setError("");
        const data = await getVehicles();

        if (!mounted) return;

        setVehicles(data);
        if (data.length > 0) {
          setSelectedVehicleId(data[0].vehicle_id);
        }
      } catch (err) {
        console.error("AI page vehicle loading error:", err);
        if (mounted) {
          setVehicles([]);
          setError("Unable to load your vehicles. Please refresh the page and try again.");
        }
      } finally {
        if (mounted) setVehiclesLoading(false);
      }
    };

    loadVehicles();

    return () => {
      mounted = false;
    };
  }, []);

  const selectedVehicle = vehicles.find(
    (vehicle) => vehicle.vehicle_id === selectedVehicleId,
  );

  const toggleVoiceInput = () => {
    setError("");
    setVoiceError("");

    if (!voiceSupported || !recognitionRef.current) {
      setVoiceError("Voice input is not supported by this browser. Please use Chrome or type your problem manually.");
      return;
    }

    if (listening) {
      recognitionRef.current.stop();
      return;
    }

    transcriptBeforeListeningRef.current = symptoms.trim();
    try {
      recognitionRef.current.start();
    } catch (err) {
      console.error("Unable to start speech recognition:", err);
      setVoiceError("Unable to start the microphone. Please try again.");
      setListening(false);
    }
  };

  const handleDiagnosis = async () => {
    setError("");
    setResult(null);

    if (selectedVehicleId === "") {
      setError("Please select a vehicle.");
      return;
    }

    const cleanedSymptoms = symptoms.trim();
    if (!cleanedSymptoms) {
      setError("Please describe your vehicle problem using text or the microphone.");
      return;
    }

    if (cleanedSymptoms.length < 5) {
      setError("Please provide a little more information about the problem.");
      return;
    }

    try {
      setDiagnosing(true);
      const response = await api.post<DiagnosisResult>("/diagnosis/", {
        vehicle_id: selectedVehicleId,
        symptoms: cleanedSymptoms,
      });
      setResult(response.data);
    } catch (err: any) {
      console.error("AI diagnosis error:", err);
      const backendMessage =
        err?.response?.data?.detail || "AI diagnosis failed. Please try again.";
      setError(backendMessage);
    } finally {
      setDiagnosing(false);
    }
  };

  const handleExample = (problem: string) => {
    if (listening) recognitionRef.current?.stop();
    setSymptoms(problem);
    setResult(null);
    setError("");
    setVoiceError("");
  };

  const handleClear = () => {
    if (listening) recognitionRef.current?.stop();
    setSymptoms("");
    setResult(null);
    setError("");
    setVoiceError("");
  };

  const priorityColors = result ? getPriorityColors(result.priority) : null;

  return (
    <AppLayout>
      <div className="ai-diagnosis-page">
        <section className="ai-diagnosis-shell">
          <button
            type="button"
            onClick={() => navigate("/dashboard")}
            style={{
              border: "none",
              background: "transparent",
              color: "var(--color-muted)",
              cursor: "pointer",
              padding: 0,
              marginBottom: "14px",
              fontSize: "14px",
            }}
          >
            <Icon name="arrowLeft" size={17} /> Back to Dashboard
          </button>

          <div style={{ marginBottom: "24px" }}>
            <div
              style={{
                fontSize: "12px",
                letterSpacing: "1.4px",
                fontWeight: 800,
              color: "var(--color-primary)",
                marginBottom: "7px",
              }}
            >
              RESQDRIVE AI
            </div>
            <h1 className="ai-diagnosis-title" style={{ margin: 0, color: "var(--color-text)" }}>
              AI Vehicle Assistant
            </h1>
            <p style={{ margin: "8px 0 0", color: "var(--color-muted)", fontSize: "15px" }}>
              Describe your vehicle problem by typing or speaking. ResQDrive AI will analyze the symptoms and suggest the next safe step.
            </p>
          </div>

          <div className="ai-diagnosis-card">
            <div
              className="ai-vehicle-grid"
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1fr) minmax(240px, 320px)",
                gap: "18px",
                alignItems: "end",
              }}
            >
              <div>
                <label
                  htmlFor="vehicle-select"
                  style={{ display: "block", fontWeight: 700, color: "var(--color-text)", marginBottom: "8px" }}
                >
                  Select Vehicle
                </label>
                <select
                  id="vehicle-select"
                  value={selectedVehicleId}
                  onChange={(event) => setSelectedVehicleId(event.target.value ? Number(event.target.value) : "")}
                  disabled={vehiclesLoading || vehicles.length === 0}
                  style={{
                    width: "100%",
                    boxSizing: "border-box",
                    padding: "13px 14px",
                    borderRadius: "12px",
                    border: "1px solid var(--color-border)",
                    background: "var(--color-surface)",
                    color: "var(--color-text)",
                    fontSize: "14px",
                  }}
                >
                  {vehiclesLoading ? (
                    <option value="">Loading vehicles...</option>
                  ) : vehicles.length === 0 ? (
                    <option value="">No vehicles found</option>
                  ) : (
                    vehicles.map((vehicle) => (
                      <option key={vehicle.vehicle_id} value={vehicle.vehicle_id}>
                        {vehicle.make} {vehicle.model} {vehicle.year ? `(${vehicle.year})` : ""}
                      </option>
                    ))
                  )}
                </select>
                {selectedVehicle && (
                  <p style={{ margin: "7px 0 0", color: "var(--color-muted)", fontSize: "12px" }}>
                    AI analysis will be linked to this vehicle.
                  </p>
                )}
              </div>

              <div
                style={{
                  padding: "13px 15px",
                  borderRadius: "12px",
                  background: "var(--color-primary-soft)",
                  border: "1px solid var(--color-primary-border)",
                  color: "var(--color-primary-hover)",
                  fontSize: "13px",
                  lineHeight: 1.5,
                }}
              >
                <strong><Icon name="mic" size={16} /> Voice + NLP</strong>
                <br />
                Speak naturally. Your browser converts speech to text and Qwen3 analyzes the problem locally.
              </div>
            </div>

            <div style={{ marginTop: "22px" }}>
              <label
                htmlFor="symptoms"
                style={{ display: "block", fontWeight: 700, color: "var(--color-text)", marginBottom: "8px" }}
              >
                Describe Your Vehicle Problem
              </label>
              <textarea
                id="symptoms"
                value={symptoms}
                onChange={(event) => {
                  setSymptoms(event.target.value);
                  setResult(null);
                  setError("");
                }}
                placeholder="Example: My car is making a grinding noise when I press the brakes..."
                rows={6}
                style={{
                  width: "100%",
                  boxSizing: "border-box",
                  resize: "vertical",
                  padding: "16px",
                  borderRadius: "14px",
                  border: listening ? "2px solid var(--color-emergency)" : "1px solid var(--color-border)",
                  outline: "none",
                  fontSize: "15px",
                  lineHeight: 1.6,
                  color: "var(--color-text)",
                  background: "var(--color-surface)",
                }}
              />

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                  flexWrap: "wrap",
                  marginTop: "10px",
                }}
              >
                <button
                  type="button"
                  onClick={toggleVoiceInput}
                  disabled={diagnosing || !voiceSupported}
                  style={{
                    border: listening ? "1px solid var(--color-emergency)" : "1px solid var(--color-border)",
                    borderRadius: "999px",
                    padding: "11px 17px",
                    background: listening ? "var(--color-emergency-soft)" : "var(--color-surface)",
                    color: listening ? "var(--color-emergency-text)" : "var(--color-text)",
                    cursor: diagnosing || !voiceSupported ? "not-allowed" : "pointer",
                    fontWeight: 800,
                    fontSize: "14px",
                    opacity: diagnosing || !voiceSupported ? 0.55 : 1,
                  }}
                >
                  <><Icon name={listening ? "stop" : "mic"} size={17} /> {listening ? "Stop Listening" : "Speak Problem"}</>
                </button>

                <span style={{ color: "var(--color-muted)", fontSize: "12px" }}>
                  {symptoms.length} characters
                </span>
              </div>

              {listening && (
                <div
                  style={{
                    marginTop: "12px",
                    padding: "12px 14px",
                    borderRadius: "12px",
                    background: "var(--color-emergency-soft)",
                    border: "1px solid var(--color-primary-border)",
                    color: "var(--color-emergency-text)",
                    fontSize: "13px",
                    fontWeight: 700,
                  }}
                >
                  <Icon name="mic" size={17} /> Listening... Speak clearly about the vehicle problem. Click Stop Listening when finished.
                </div>
              )}

              {voiceError && (
                <div
                  style={{
                    marginTop: "12px",
                    padding: "12px 14px",
                    borderRadius: "12px",
                    background: "var(--color-warning-soft)",
                    border: "1px solid var(--color-warning)",
                    color: "var(--color-warning-text)",
                    fontSize: "13px",
                  }}
                >
                  {voiceError}
                </div>
              )}

              {!voiceSupported && (
                <p style={{ margin: "10px 0 0", color: "var(--color-muted)", fontSize: "12px" }}>
                  Voice input is unavailable in this browser. Use Google Chrome for microphone support.
                </p>
              )}
            </div>

            <div style={{ marginTop: "22px" }}>
              <div style={{ fontWeight: 700, color: "var(--color-text)", fontSize: "13px", marginBottom: "10px" }}>
                Try an example
              </div>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                {exampleProblems.map((problem) => (
                  <button
                    key={problem}
                    type="button"
                    onClick={() => handleExample(problem)}
                    style={{
                      border: "1px solid var(--color-primary-border)",
                      borderRadius: "999px",
                      padding: "8px 12px",
                      background: "var(--color-primary-soft)",
                      color: "var(--color-primary)",
                      cursor: "pointer",
                      fontSize: "12px",
                      fontWeight: 600,
                    }}
                  >
                    {problem}
                  </button>
                ))}
              </div>
            </div>

            {error && (
              <div
                style={{
                  marginTop: "20px",
                  padding: "13px 15px",
                  borderRadius: "12px",
                  background: "var(--color-emergency-soft)",
                  border: "1px solid var(--color-primary-border)",
                  color: "var(--color-emergency-text)",
                  fontSize: "14px",
                }}
              >
                {error}
              </div>
            )}

            <div style={{ display: "flex", gap: "12px", marginTop: "24px", flexWrap: "wrap" }}>
              <button
                className="primary-button"
                type="button"
                onClick={handleDiagnosis}
                disabled={diagnosing || vehiclesLoading || vehicles.length === 0}
              >
                <><Icon name={diagnosing ? "sparkles" : "bot"} size={17} /> {diagnosing ? "Analyzing..." : "Analyze with AI"}</>
              </button>

              <button
                className="secondary-button"
                type="button"
                onClick={handleClear}
              >
                Clear
              </button>
            </div>
          </div>

          {result && (
            <div className="ai-diagnosis-card ai-result-card">
              <div style={{ display: "flex", justifyContent: "space-between", gap: "16px", alignItems: "flex-start", flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: "12px", letterSpacing: "1.3px", fontWeight: 700, color: "var(--color-primary)", marginBottom: "6px" }}>
                    RESQDRIVE AI RESULT
                  </div>
                  <h2 style={{ margin: 0, fontSize: "24px", color: "var(--color-text)" }}>AI Diagnosis</h2>
                </div>
                <span
                  style={{
                    padding: "8px 13px",
                    borderRadius: "999px",
                    background: priorityColors?.background,
                    color: priorityColors?.color,
                    fontSize: "12px",
                    fontWeight: 800,
                    letterSpacing: "0.7px",
                  }}
                >
                  {result.priority.toUpperCase()} PRIORITY
                </span>
              </div>

              <div style={{ marginTop: "24px", padding: "20px", borderRadius: "16px", background: "var(--color-primary-soft)", border: "1px solid var(--color-primary-border)" }}>
                <div style={{ fontSize: "12px", fontWeight: 700, color: "var(--color-muted)", marginBottom: "7px" }}>IDENTIFIED PROBLEM</div>
                <div style={{ fontSize: "19px", fontWeight: 700, color: "var(--color-text)" }}>{result.diagnosis}</div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px", marginTop: "18px" }}>
                <div style={{ padding: "18px", borderRadius: "14px", background: "var(--color-background)", border: "1px solid var(--color-border)" }}>
                  <div style={{ color: "var(--color-muted)", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>RECOMMENDED SERVICE</div>
                  <strong style={{ color: "var(--color-text)", fontSize: "17px" }}><Icon name="wrench" size={17} /> {formatService(result.recommended_service)}</strong>
                </div>
                <div style={{ padding: "18px", borderRadius: "14px", background: "var(--color-background)", border: "1px solid var(--color-border)" }}>
                  <div style={{ color: "var(--color-muted)", fontSize: "12px", fontWeight: 700, marginBottom: "6px" }}>AI CONFIDENCE</div>
                  <strong style={{ color: "var(--color-text)", fontSize: "17px" }}><Icon name="bot" size={17} /> {result.confidence}%</strong>
                </div>
              </div>

              <div style={{ marginTop: "24px" }}>
                <h3 style={{ margin: "0 0 12px", color: "var(--color-text)", fontSize: "18px" }}>Possible Causes</h3>
                {result.possible_causes.length > 0 ? (
                  <ul style={{ margin: 0, paddingLeft: "22px", color: "var(--color-muted)", lineHeight: 1.8 }}>
                    {result.possible_causes.map((cause, index) => <li key={`${cause}-${index}`}>{cause}</li>)}
                  </ul>
                ) : (
                  <p style={{ color: "var(--color-muted)" }}>No specific possible causes were returned.</p>
                )}
              </div>

              <div style={{ marginTop: "24px", padding: "18px", borderRadius: "14px", background: "var(--color-warning-soft)", border: "1px solid var(--color-warning)" }}>
                <h3 style={{ margin: "0 0 8px", color: "var(--color-warning-text)", fontSize: "17px" }}><Icon name="alert" size={18} /> Safety Advice</h3>
                <p style={{ margin: 0, color: "var(--color-warning-text)", lineHeight: 1.6 }}>{result.advice}</p>
              </div>

              <div style={{ marginTop: "18px", padding: "14px 16px", borderRadius: "12px", background: "var(--color-background)", color: "var(--color-muted)", fontSize: "12px", lineHeight: 1.5 }}>
                AI provides assistance based on the symptoms you describe. It does not replace a professional mechanical inspection.
              </div>

              <div style={{ marginTop: "24px", paddingTop: "22px", borderTop: "1px solid var(--color-border)" }}>
                <button
                  type="button"
                  onClick={() =>
                    navigate("/emergency/create", {
                      state: {
                        aiDiagnosis: result.diagnosis,
                        aiPriority: result.priority,
                        aiService: result.recommended_service,
                        aiAdvice: result.advice,
                        aiCauses: result.possible_causes,
                      },
                    })
                  }
                  className="emergency-button"
                  style={{ width: "100%", border: "none", borderRadius: "12px", padding: "15px 20px", background: "var(--color-emergency)", color: "var(--color-surface)", cursor: "pointer", fontWeight: 800, fontSize: "15px" }}
                >
                  <><Icon name="siren" size={18} /> Request Roadside Assistance</>
                </button>
                <p style={{ textAlign: "center", color: "var(--color-muted)", fontSize: "12px", margin: "10px 0 0" }}>
                  This will open the emergency assistance flow.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </AppLayout>
  );
}
