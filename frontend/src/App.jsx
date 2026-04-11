import { useCallback, useEffect, useRef, useState } from "react";
import { apiUrl } from "./apiBase";
import "./App.css";

const MAX_MS = 10 * 60 * 1000;
/** Whisper + Gemini can take several minutes — match Vite proxy (10m). */
const API_TIMEOUT_MS = 10 * 60 * 1000;

async function apiJson(path, options = {}) {
  const { timeoutMs = API_TIMEOUT_MS, ...fetchOpts } = options;
  const init = { ...fetchOpts };
  if (typeof AbortSignal !== "undefined" && AbortSignal.timeout) {
    init.signal = AbortSignal.timeout(timeoutMs);
  }
  const res = await fetch(apiUrl(path), init);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const base = data.error || res.statusText || "Request failed";
    let detail = "";
    if (data.detail != null && data.detail !== "") {
      detail =
        typeof data.detail === "object"
          ? JSON.stringify(data.detail)
          : String(data.detail);
    }
    const fix = data.fix ? String(data.fix) : "";
    const parts = [base];
    if (detail && !base.includes(detail)) parts.push(detail);
    if (fix) parts.push(fix);
    const msg = parts.join(" — ");
    throw new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data;
}

export default function App() {
  const [mode, setMode] = useState("resume");
  const [roles, setRoles] = useState([]);
  const [bankRole, setBankRole] = useState("");
  const [roleInput, setRoleInput] = useState("");
  const [webUrl, setWebUrl] = useState("");
  const [resumeFile, setResumeFile] = useState(null);
  const [step, setStep] = useState("setup");
  const [question, setQuestion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [elapsedMs, setElapsedMs] = useState(0);
  const [result, setResult] = useState(null);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [liveCaptionsAvailable, setLiveCaptionsAvailable] = useState(false);
  /** Tracks how the current session started so we can load another question. */
  const [sessionSource, setSessionSource] = useState(null);
  const [questionRound, setQuestionRound] = useState(0);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const timerRef = useRef(null);
  const startRef = useRef(0);
  const recognitionRef = useRef(null);
  const liveFinalRef = useRef("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiJson("/api/roles");
        if (!cancelled) {
          setRoles(data.roles || []);
          if (data.roles?.length) setBankRole(data.roles[0]);
        }
      } catch {
        /* optional for resume-only path */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const stopLiveRecognition = useCallback(() => {
    const rec = recognitionRef.current;
    if (rec) {
      try {
        rec.onresult = null;
        rec.onend = null;
        rec.onerror = null;
        rec.stop();
      } catch {
        /* ignore */
      }
      recognitionRef.current = null;
    }
  }, []);

  const stopTracks = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const clearRecorderTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    return () => {
      clearRecorderTimer();
      stopLiveRecognition();
      stopTracks();
      mediaRecorderRef.current = null;
    };
  }, [clearRecorderTimer, stopLiveRecognition, stopTracks]);

  const fetchResumeQuestion = async () => {
    const r = roleInput.trim();
    if (!r) {
      throw new Error(
        "Enter the role you are targeting (e.g. Java Automation Testing)."
      );
    }
    if (!resumeFile) {
      throw new Error(
        "Choose a resume file (PDF, DOCX, or TXT), or finish and start again from the Resume tab."
      );
    }
    const fd = new FormData();
    fd.append("role", r);
    fd.append("resume", resumeFile);
    return apiJson("/api/prepare-from-resume", {
      method: "POST",
      body: fd,
      timeoutMs: API_TIMEOUT_MS,
    });
  };

  const fetchWebQuestion = async () => {
    const r = roleInput.trim();
    const u = webUrl.trim();
    if (!r) {
      throw new Error("Enter the target role.");
    }
    if (!u) {
      throw new Error("Enter a page URL to scrape (https://…).");
    }
    return apiJson("/api/prepare-from-web", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ role: r, source_url: u }),
      timeoutMs: API_TIMEOUT_MS,
    });
  };

  const prepareFromResume = async () => {
    setError("");
    setLoading(true);
    setResult(null);
    setQuestion(null);
    try {
      const q = await fetchResumeQuestion();
      setSessionSource("resume");
      setQuestionRound(1);
      setQuestion(q);
      setStep("interview");
    } catch (e) {
      setError(e.message || "Could not prepare interview");
    } finally {
      setLoading(false);
    }
  };

  const prepareFromWeb = async () => {
    setError("");
    setLoading(true);
    setResult(null);
    setQuestion(null);
    try {
      const q = await fetchWebQuestion();
      setSessionSource("web");
      setQuestionRound(1);
      setQuestion(q);
      setStep("interview");
    } catch (e) {
      if (e.name === "TimeoutError" || e.name === "AbortError") {
        setError("Request timed out — try again or shorten the page.");
      } else {
        setError(e.message || "Could not prepare from web");
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchBankQuestion = async () => {
    setError("");
    setLoading(true);
    setResult(null);
    setQuestion(null);
    try {
      const q = await apiJson(
        `/api/get-question?role=${encodeURIComponent(bankRole)}`
      );
      setSessionSource("bank");
      setQuestionRound(1);
      setQuestion(q);
      setStep("interview");
    } catch (e) {
      setError(e.message || "Failed to load question");
    } finally {
      setLoading(false);
    }
  };

  const nextQuestion = async () => {
    if (!sessionSource) {
      setError("Start an interview from the tabs above first.");
      return;
    }
    setError("");
    setResult(null);
    setLiveTranscript("");
    liveFinalRef.current = "";
    setLoading(true);
    try {
      let q;
      if (sessionSource === "bank") {
        q = await apiJson(
          `/api/get-question?role=${encodeURIComponent(bankRole)}`
        );
      } else if (sessionSource === "resume") {
        q = await fetchResumeQuestion();
      } else {
        q = await fetchWebQuestion();
      }
      setQuestionRound((n) => n + 1);
      setQuestion(q);
      setStep("interview");
    } catch (e) {
      if (e.name === "TimeoutError" || e.name === "AbortError") {
        setError("Request timed out — try again.");
      } else {
        setError(e.message || "Could not load the next question");
      }
    } finally {
      setLoading(false);
    }
  };

  const uploadAnswer = async (blob, hitMax) => {
    setError("");
    setLoading(true);
    try {
      const fd = new FormData();
      fd.append("audio", blob, "answer.webm");
      fd.append("question_id", question.question_id);
      const data = await apiJson("/api/analyze-answer", {
        method: "POST",
        body: fd,
        timeoutMs: API_TIMEOUT_MS,
      });
      if (hitMax) data._note = "Stopped at max length (10 min).";
      setResult(data);
      setStep("results");
    } catch (e) {
      setError(e.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const stopRecording = (fromMax = false) => {
    const mr = mediaRecorderRef.current;
    if (!mr || mr.state === "inactive") {
      clearRecorderTimer();
      stopLiveRecognition();
      setRecording(false);
      stopTracks();
      return;
    }
    stopLiveRecognition();
    mr.onstop = async () => {
      clearRecorderTimer();
      setRecording(false);
      stopTracks();
      mediaRecorderRef.current = null;
      const blob = new Blob(chunksRef.current, {
        type: mr.mimeType || "audio/webm",
      });
      chunksRef.current = [];
      if (blob.size < 256) {
        setError("Recording too short. Try again.");
        return;
      }
      await uploadAnswer(blob, fromMax);
    };
    mr.stop();
  };

  const startRecording = async () => {
    setError("");
    chunksRef.current = [];
    setLiveTranscript("");
    liveFinalRef.current = "";
    stopLiveRecognition();
    const SR =
      typeof window !== "undefined" &&
      (window.SpeechRecognition || window.webkitSpeechRecognition);
    setLiveCaptionsAvailable(Boolean(SR));
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : "audio/webm";
      const mr = new MediaRecorder(stream, { mimeType: mime });
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (ev) => {
        if (ev.data.size) chunksRef.current.push(ev.data);
      };
      mr.start(250);
      setRecording(true);
      if (SR) {
        try {
          const rec = new SR();
          rec.continuous = true;
          rec.interimResults = true;
          rec.lang = (navigator.language || "en-US").replace(/_/g, "-");
          rec.onresult = (event) => {
            let interim = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
              const tr = event.results[i][0].transcript;
              if (event.results[i].isFinal) liveFinalRef.current += tr;
              else interim += tr;
            }
            setLiveTranscript((liveFinalRef.current + interim).trim());
          };
          rec.onerror = () => {};
          rec.start();
          recognitionRef.current = rec;
        } catch {
          setLiveCaptionsAvailable(false);
        }
      }
      setElapsedMs(0);
      startRef.current = Date.now();
      timerRef.current = setInterval(() => {
        const e = Date.now() - startRef.current;
        setElapsedMs(e);
        if (e >= MAX_MS) stopRecording(true);
      }, 200);
    } catch (e) {
      setError(
        e.name === "NotAllowedError"
          ? "Microphone permission denied."
          : "Could not start recording."
      );
    }
  };

  const finishInterview = () => {
    setResult(null);
    setQuestion(null);
    setResumeFile(null);
    setWebUrl("");
    setLiveTranscript("");
    liveFinalRef.current = "";
    setSessionSource(null);
    setQuestionRound(0);
    setStep("setup");
  };

  const formatTime = (ms) => {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    const r = s % 60;
    return `${m}:${r.toString().padStart(2, "0")}`;
  };

  return (
    <div className="app">
      <h1>AI Interview Coach</h1>
      <p className="subtitle">
        Start from resume, web, or the question bank. After each answer you can take
        another question or finish the interview when you choose. Speech goes to the
        server (OpenAI Whisper, or Groq Whisper as fallback); feedback uses Gemini,
        Groq, or Hugging Face.
      </p>

      {error ? <div className="error">{error}</div> : null}

      {step === "setup" && (
        <>
          <div className="card mode-tabs mode-tabs-3">
            <button
              type="button"
              className={`tab${mode === "resume" ? " tab-active" : ""}`}
              onClick={() => {
                setMode("resume");
                setError("");
              }}
            >
              Resume
            </button>
            <button
              type="button"
              className={`tab${mode === "web" ? " tab-active" : ""}`}
              onClick={() => {
                setMode("web");
                setError("");
              }}
            >
              Web page
            </button>
            <button
              type="button"
              className={`tab${mode === "bank" ? " tab-active" : ""}`}
              onClick={() => {
                setMode("bank");
                setError("");
              }}
            >
              Bank
            </button>
          </div>

          {mode === "resume" && (
            <div className="card">
              <label htmlFor="role-input">Target role (type freely)</label>
              <input
                id="role-input"
                type="text"
                className="text-input"
                placeholder="e.g. Java Automation Testing, Staff ML Engineer"
                value={roleInput}
                onChange={(e) => setRoleInput(e.target.value)}
                autoComplete="organization-title"
              />
              <label htmlFor="resume" style={{ marginTop: "1rem" }}>
                Resume (PDF, DOCX, or TXT)
              </label>
              <input
                id="resume"
                type="file"
                className="file-input"
                accept=".pdf,.docx,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
                onChange={(e) =>
                  setResumeFile(e.target.files?.[0] || null)
                }
              />
              {resumeFile ? (
                <p className="file-name">{resumeFile.name}</p>
              ) : null}
              <div className="row" style={{ marginTop: "1.25rem" }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={prepareFromResume}
                  disabled={loading}
                >
                  {loading ? "Analyzing resume…" : "Analyze & get question"}
                </button>
              </div>
              <p className="hint">
                We read your resume, summarize it, and generate a question. After
                feedback, use Next question for another round, or Finish interview to
                stop.
              </p>
            </div>
          )}

          {mode === "web" && (
            <div className="card">
              <label htmlFor="role-web">Target role</label>
              <input
                id="role-web"
                type="text"
                className="text-input"
                placeholder="e.g. Java Automation Testing"
                value={roleInput}
                onChange={(e) => setRoleInput(e.target.value)}
              />
              <label htmlFor="web-url" style={{ marginTop: "1rem" }}>
                Public page URL (https)
              </label>
              <input
                id="web-url"
                type="url"
                className="text-input"
                placeholder="https://raw.githubusercontent.com/.../questions.md"
                value={webUrl}
                onChange={(e) => setWebUrl(e.target.value)}
                autoComplete="url"
              />
              <div className="row" style={{ marginTop: "1.25rem" }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={prepareFromWeb}
                  disabled={loading}
                >
                  {loading ? "Scraping & generating…" : "Scrape + get question"}
                </button>
              </div>
              <p className="hint">
                We fetch the page safely, extract text, and generate a question with a
                reference answer. Continue with Next question after each result, or
                Finish interview when you are done.
              </p>
            </div>
          )}

          {mode === "bank" && (
            <div className="card">
              <label htmlFor="bank-role">Preset role category</label>
              <select
                id="bank-role"
                value={bankRole}
                onChange={(e) => setBankRole(e.target.value)}
                disabled={!roles.length}
              >
                {!roles.length ? (
                  <option value="">No bank loaded — use Resume tab</option>
                ) : (
                  roles.map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))
                )}
              </select>
              <div className="row" style={{ marginTop: "1.25rem" }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={fetchBankQuestion}
                  disabled={loading || !roles.length}
                >
                  {loading ? "Loading…" : "Get a random question"}
                </button>
              </div>
              <p className="hint">
                Pick a category (e.g. Java Automation Testing). After each graded
                answer, choose Next question or Finish interview.
              </p>
            </div>
          )}
        </>
      )}

      {step === "interview" && question && (
        <div className="card">
          {question.resume_summary ? (
            <div className="insight">
              <h3 className="insight-title">
                {question.source === "web"
                  ? "Page insight"
                  : question.source === "resume"
                    ? "Resume insight"
                    : "Context"}
              </h3>
              <p className="insight-body">{question.resume_summary}</p>
            </div>
          ) : null}
          {question.source_url ? (
            <p className="role-line">
              <strong>Source:</strong>{" "}
              <a
                href={question.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="source-link"
              >
                {question.source_url}
              </a>
            </p>
          ) : null}
          {question.role &&
          (question.source === "resume" || question.source === "web") ? (
            <p className="role-line">
              <strong>Role:</strong> {question.role}
            </p>
          ) : null}
          {questionRound > 0 ? (
            <p className="round-line">
              Question {questionRound}
              {sessionSource ? ` · ${sessionSource === "bank" ? "bank" : sessionSource === "resume" ? "resume" : "web"}` : ""}
            </p>
          ) : null}
          <p className="question-text">{question.question_text}</p>
          <div className="row">
            {!recording ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={startRecording}
                disabled={loading}
              >
                Record answer
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-danger"
                onClick={() => stopRecording(false)}
                disabled={loading}
              >
                Stop
              </button>
            )}
            {recording && (
              <span className="timer">{formatTime(elapsedMs)} / 10:00</span>
            )}
          </div>
          {recording && liveCaptionsAvailable ? (
            <div className="live-transcript" aria-live="polite">
              <span className="live-transcript-label">Live caption</span>
              <p className="live-transcript-body">
                {liveTranscript || "Listening…"}
              </p>
            </div>
          ) : recording && !liveCaptionsAvailable ? (
            <p className="hint live-caption-hint">
              Live captions need a Chromium-based browser (Chrome/Edge). Recording
              still works; your full answer is transcribed after you press Stop.
            </p>
          ) : null}
          <p
            className={`status${recording ? " recording" : ""}`}
            role="status"
            aria-live="polite"
          >
            {loading
              ? "Transcribing and analyzing…"
              : recording
                ? "Recording… keep going until you press Stop."
                : "Press Record, then Stop when you are done (up to 10 minutes)."}
          </p>
        </div>
      )}

      {step === "results" && result && (
        <div className="card">
          {result._note ? (
            <p className="status" style={{ marginBottom: "1rem" }}>
              {result._note}
            </p>
          ) : null}
          <div className="feedback-block">
            <h3>Your answer (transcript)</h3>
            {result.transcript ? (
              <p className="transcript transcript-block">{result.transcript}</p>
            ) : (
              <p className="muted">No transcript returned.</p>
            )}
            {result.improved_answer_example ? (
              <>
                <h3>How to say it better</h3>
                <p className="improved-sample">{result.improved_answer_example}</p>
              </>
            ) : null}
            <h3>Ratings (1–5)</h3>
            <div className="scores">
              {["clarity", "correctness", "completeness"].map((k) => (
                <div key={k} className="score-pill">
                  <span>{result.scores?.[k] ?? "—"}</span>
                  <small>{k}</small>
                </div>
              ))}
            </div>
            <h3>Summary</h3>
            <p>{result.feedback_summary}</p>
            <h3>Suggestions</h3>
            <p>{result.suggestions_for_improvement}</p>
            <h3>Reference answer</h3>
            <div className="perfect">{result.perfect_answer}</div>
          </div>
          <div className="row row-actions" style={{ marginTop: "1.5rem" }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={nextQuestion}
              disabled={loading || !sessionSource}
            >
              {loading ? "Loading…" : "Next question"}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={finishInterview}
              disabled={loading}
            >
              Finish interview
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
