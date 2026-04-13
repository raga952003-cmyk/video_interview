import { useCallback, useEffect, useRef, useState } from "react";
import { apiUrl } from "./apiBase";
import "./App.css";

const MAX_MS = 10 * 60 * 1000;
/** Whisper + Gemini can take several minutes — match Vite proxy (10m). */
const API_TIMEOUT_MS = 10 * 60 * 1000;

/** VP8 first — VP9 record often fails on some Windows/GPU setups. */
function createVideoMediaRecorder(stream) {
  if (typeof MediaRecorder === "undefined") {
    throw new Error("This browser does not support MediaRecorder.");
  }
  const types = [
    "video/webm;codecs=vp8,opus",
    "video/webm;codecs=vp9,opus",
    "video/webm",
  ];
  for (const mimeType of types) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      try {
        return new MediaRecorder(stream, { mimeType });
      } catch {
        /* try next */
      }
    }
  }
  return new MediaRecorder(stream);
}

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
  /** Tracks how the current session started so we can load another question. */
  const [sessionSource, setSessionSource] = useState(null);
  const [questionRound, setQuestionRound] = useState(0);
  /** Shared by Resume + Web multi-question runs */
  const [sessionRunId, setSessionRunId] = useState(null);
  /** Each graded answer in this interview (all modes). */
  const [sessionHistory, setSessionHistory] = useState([]);

  const mediaRecorderRef = useRef(null);
  /** Bank: IDs already seen this session (avoid immediate repeats). */
  const bankSeenIdsRef = useRef(new Set());
  const chunksRef = useRef([]);
  const streamRef = useRef(null);
  const videoPreviewRef = useRef(null);
  /** Interview always requests camera + mic when available (no checkbox). */
  /** Set when a clip starts so onstop always knows audio vs video upload. */
  const recordingIsVideoRef = useRef(false);
  /** Bump after a video recording stops so preview `getUserMedia` runs again. */
  const [videoPreviewKey, setVideoPreviewKey] = useState(0);
  /** After Stop: preview locally; "Next" uploads and stores on server. */
  const [pendingRecording, setPendingRecording] = useState(null);
  /** True only when preview has a live video track — interview requires camera on to record. */
  const [cameraReady, setCameraReady] = useState(false);
  const timerRef = useRef(null);
  const startRef = useRef(0);
  const recognitionRef = useRef(null);

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
    if (videoPreviewRef.current) {
      videoPreviewRef.current.srcObject = null;
    }
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

  /** Start camera preview as soon as video mode is on (avoids black box + second getUserMedia on Record). */
  useEffect(() => {
    if (step !== "interview") {
      return undefined;
    }
    let cancelled = false;
    const startPreview = async () => {
      try {
        if (!navigator.mediaDevices?.getUserMedia) {
          setError("This browser does not support camera/microphone access.");
          return;
        }
        let stream;
        try {
          stream = await navigator.mediaDevices.getUserMedia({
            audio: true,
            video: {
              facingMode: { ideal: "user" },
              width: { ideal: 640 },
              height: { ideal: 480 },
            },
          });
          if (cancelled) {
            stream.getTracks().forEach((t) => t.stop());
            return;
          }
          const hasVideo = stream
            .getVideoTracks()
            .some((t) => t.readyState === "live");
          if (!hasVideo) {
            stream.getTracks().forEach((t) => t.stop());
            if (!cancelled) {
              setCameraReady(false);
              setError(
                "A working camera is required. Your device did not provide a video track."
              );
            }
            return;
          }
          setCameraReady(true);
          setError("");
        } catch (e1) {
          if (cancelled) return;
          setCameraReady(false);
          const name = e1?.name || "";
          setError(
            name === "NotAllowedError" || name === "PermissionDeniedError"
              ? "Camera and microphone are required. Allow both when your browser asks — you cannot continue without the camera on."
              : name === "NotReadableError" || name === "TrackStartError"
                ? "Camera or microphone is in use. Close other apps using them, then use Retry camera."
                : `Could not open camera: ${e1?.message || String(e1)}`
          );
          return;
        }
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        const el = videoPreviewRef.current;
        if (el) {
          el.srcObject = stream;
          el.muted = true;
          const play = () => el.play().catch(() => {});
          el.onloadedmetadata = () => play();
          play();
        }
      } catch (e) {
        if (!cancelled) {
          setError(`Could not open camera: ${e?.message || String(e)}`);
        }
      }
    };
    startPreview();
    return () => {
      cancelled = true;
      setCameraReady(false);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
      const el = videoPreviewRef.current;
      if (el) {
        el.onloadedmetadata = null;
        el.srcObject = null;
      }
    };
  }, [step, videoPreviewKey]);

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

  const flushPendingRecording = () => {
    setPendingRecording((prev) => {
      if (prev?.objectUrl) URL.revokeObjectURL(prev.objectUrl);
      return null;
    });
  };

  const prepareFromResume = async () => {
    setError("");
    setLoading(true);
    flushPendingRecording();
    setResult(null);
    setQuestion(null);
    setSessionHistory([]);
    try {
      const q = await fetchResumeQuestion();
      setSessionSource("resume");
      setQuestionRound(1);
      setSessionRunId(q.interview_run_id || q.question_id || null);
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
    flushPendingRecording();
    setResult(null);
    setQuestion(null);
    setSessionHistory([]);
    try {
      const q = await fetchWebQuestion();
      setSessionSource("web");
      setQuestionRound(1);
      setSessionRunId(q.interview_run_id || q.question_id || null);
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
    flushPendingRecording();
    setResult(null);
    setQuestion(null);
    bankSeenIdsRef.current = new Set();
    setSessionHistory([]);
    try {
      const q = await apiJson(
        `/api/get-question?role=${encodeURIComponent(bankRole)}`
      );
      setSessionSource("bank");
      setQuestionRound(1);
      setSessionRunId(null);
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
    flushPendingRecording();
    setResult(null);
    setLoading(true);
    try {
      let q;
      if (sessionSource === "bank") {
        if (question?.question_id) {
          bankSeenIdsRef.current.add(question.question_id);
        }
        const seen = [...bankSeenIdsRef.current];
        const ex =
          seen.length > 0
            ? `&exclude=${encodeURIComponent(seen.join(","))}`
            : "";
        q = await apiJson(
          `/api/get-question?role=${encodeURIComponent(bankRole)}${ex}`
        );
      } else if (sessionSource === "resume") {
        const rid = sessionRunId || question?.interview_run_id;
        if (!rid) {
          throw new Error("Missing interview run. Start again from the Resume tab.");
        }
        q = await apiJson("/api/resume-next-question", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ interview_run_id: rid }),
          timeoutMs: API_TIMEOUT_MS,
        });
      } else {
        const wid = sessionRunId || question?.interview_run_id;
        if (!wid) {
          throw new Error("Missing web session. Start again from the Web page tab.");
        }
        q = await apiJson("/api/web-next-question", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ interview_run_id: wid }),
          timeoutMs: API_TIMEOUT_MS,
        });
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

  const uploadAnswer = async (blob, hitMax, isVideo) => {
    setError("");
    setLoading(true);
    try {
      const fd = new FormData();
      if (isVideo) {
        fd.append("video", blob, "answer.webm");
      } else {
        fd.append("audio", blob, "answer.webm");
      }
      fd.append("question_id", question.question_id);
      const data = await apiJson("/api/analyze-answer", {
        method: "POST",
        body: fd,
        timeoutMs: API_TIMEOUT_MS,
      });
      if (hitMax) data._note = "Stopped at max length (10 min).";
      const sourceLabel =
        sessionSource === "bank"
          ? "Question bank"
          : sessionSource === "resume"
            ? "Resume"
            : "Web page";
      setSessionHistory((h) => [
        ...h,
        {
          round: questionRound,
          source: sessionSource,
          sourceLabel,
          question_kind: question?.question_kind,
          question_text: question?.question_text,
          question_id: question?.question_id,
          bank_role_category: sessionSource === "bank" ? bankRole : null,
          transcript: data.transcript,
          scores: data.scores,
          feedback_summary: data.feedback_summary,
          suggestions_for_improvement: data.suggestions_for_improvement,
          improved_answer_example: data.improved_answer_example,
          perfect_answer: data.perfect_answer,
          note: data._note,
          recording_id: data.recording_id,
          recording_token: data.recording_token,
          recording_media_kind: data.recording_media_kind,
        },
      ]);
      setResult(data);
      setStep("results");
    } catch (e) {
      setError(e.message || "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const discardPendingRecording = () => {
    flushPendingRecording();
    setVideoPreviewKey((k) => k + 1);
  };

  const handleSavePendingRecording = async () => {
    if (!pendingRecording || !question) return;
    const pr = pendingRecording;
    URL.revokeObjectURL(pr.objectUrl);
    setPendingRecording(null);
    await uploadAnswer(pr.blob, pr.hitMax, pr.isVideo);
  };

  const stopRecording = (fromMax = false) => {
    const mr = mediaRecorderRef.current;
    if (!mr || mr.state === "inactive") {
      clearRecorderTimer();
      stopLiveRecognition();
      setRecording(false);
      stopTracks();
      setVideoPreviewKey((k) => k + 1);
      return;
    }
    stopLiveRecognition();
    mr.onstop = async () => {
      clearRecorderTimer();
      setRecording(false);
      stopTracks();
      mediaRecorderRef.current = null;
      const wasVideo = recordingIsVideoRef.current;
      const blob = new Blob(chunksRef.current, {
        type: mr.mimeType || "audio/webm",
      });
      chunksRef.current = [];
      if (blob.size < 256) {
        setError("Recording too short. Try again.");
        setVideoPreviewKey((k) => k + 1);
        return;
      }
      setPendingRecording((prev) => {
        if (prev?.objectUrl) URL.revokeObjectURL(prev.objectUrl);
        return {
          blob,
          objectUrl: URL.createObjectURL(blob),
          isVideo: wasVideo,
          hitMax: fromMax,
        };
      });
      setVideoPreviewKey((k) => k + 1);
    };
    mr.stop();
  };

  const startRecording = async () => {
    setError("");
    chunksRef.current = [];
    stopLiveRecognition();
    recordingIsVideoRef.current = true;
    try {
      if (!cameraReady) {
        setError(
          "Turn on your camera and allow access before recording. Use Retry camera if needed."
        );
        return;
      }
      if (!navigator.mediaDevices?.getUserMedia) {
        setError("This browser does not support recording from microphone/camera.");
        return;
      }
      let stream;
      const existing = streamRef.current;
      const vTracks = existing?.getVideoTracks?.() ?? [];
      const hasLiveVideo = vTracks.some((t) => t.readyState === "live");
      if (hasLiveVideo) {
        stream = existing;
      } else {
        stopTracks();
        stream = await navigator.mediaDevices.getUserMedia({
          audio: true,
          video: { facingMode: "user" },
        });
        const ok = stream.getVideoTracks().some((t) => t.readyState === "live");
        if (!ok) {
          stream.getTracks().forEach((t) => t.stop());
          setCameraReady(false);
          setError(
            "Camera is required. Allow camera access, then use Retry camera below."
          );
          return;
        }
        streamRef.current = stream;
        const el = videoPreviewRef.current;
        if (el) {
          el.srcObject = stream;
          el.onloadedmetadata = () => el.play().catch(() => {});
          await el.play().catch(() => {});
        }
        setCameraReady(true);
      }

      const mr = createVideoMediaRecorder(stream);
      mediaRecorderRef.current = mr;
      mr.ondataavailable = (ev) => {
        if (ev.data.size) chunksRef.current.push(ev.data);
      };
      try {
        mr.start(200);
      } catch (recErr) {
        stopTracks();
        setError(
          `Recorder did not start: ${recErr?.message || recErr}. Try another browser or turn off other apps using the camera.`
        );
        return;
      }
      setRecording(true);
      /* Live Web Speech captions off while recording video+mic (browser / stability). */
      setElapsedMs(0);
      startRef.current = Date.now();
      timerRef.current = setInterval(() => {
        const e = Date.now() - startRef.current;
        setElapsedMs(e);
        if (e >= MAX_MS) stopRecording(true);
      }, 200);
    } catch (e) {
      const name = e?.name || "";
      setError(
        name === "NotAllowedError" || name === "PermissionDeniedError"
          ? "Allow camera and microphone when the browser asks."
          : name === "NotReadableError" || name === "TrackStartError"
            ? "Camera or microphone is busy. Close other tabs or apps using them, then try again."
            : `Could not start recording: ${e?.message || String(e)}`
      );
    }
  };

  const resetSessionToSetup = () => {
    flushPendingRecording();
    setResult(null);
    setQuestion(null);
    setResumeFile(null);
    setWebUrl("");
    setSessionSource(null);
    setQuestionRound(0);
    setSessionRunId(null);
    bankSeenIdsRef.current = new Set();
    setSessionHistory([]);
    setStep("setup");
  };

  /** End interview: show full history if any answers were graded. */
  const finishInterview = () => {
    if (sessionHistory.length > 0) {
      setStep("summary");
      return;
    }
    resetSessionToSetup();
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
        another question or finish the interview when you choose. The interview step{" "}
        <strong>requires your camera and microphone on</strong> — you cannot record
        without video. The coach <strong>does not analyze your face or body language</strong>{" "}
        — it transcribes speech and grades your answer as text. Transcription:{" "}
        <code className="inline-code">LOCAL_WHISPER=1</code> or
        OpenAI / Groq Whisper. Feedback: Gemini, Groq, or Hugging Face.
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
                We summarize your resume, then your <strong>first question is a brief
                self-introduction</strong> tailored to you. After that,{" "}
                <strong>technical questions</strong> are generated from your resume
                (no repeats in-session). Use Next question to continue or Finish to
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
                Large question pools (e.g. Java Automation Testing) rotate without
                repeating the same item until you have seen them all. Next question
                after each result, or Finish interview.
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
              {sessionSource
                ? ` · ${sessionSource === "bank" ? "bank" : sessionSource === "resume" ? "resume" : "web"}`
                : ""}
              {question.question_kind === "intro"
                ? " · Self-introduction"
                : question.question_kind === "technical"
                  ? " · Technical"
                  : question.question_kind === "web" ||
                      question.question_kind === "web_followup"
                    ? " · From page"
                    : ""}
            </p>
          ) : null}
          <p className="question-text">{question.question_text}</p>
          {pendingRecording ? (
            <>
              <h3 className="review-block-title">Preview your answer</h3>
              <p className="hint">
                Play it back, then tap <strong>Next</strong> to store it on the server and
                run transcription + coaching. <strong>Record again</strong> discards this
                clip.
              </p>
              {pendingRecording.isVideo ? (
                <video
                  className="review-media"
                  src={pendingRecording.objectUrl}
                  controls
                  playsInline
                />
              ) : (
                <audio
                  className="review-audio"
                  src={pendingRecording.objectUrl}
                  controls
                />
              )}
              <div className="row" style={{ marginTop: "1rem" }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleSavePendingRecording}
                  disabled={loading}
                >
                  {loading ? "Please wait…" : "Next"}
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={discardPendingRecording}
                  disabled={loading}
                >
                  Record again
                </button>
              </div>
            </>
          ) : null}
          {!pendingRecording ? (
            <>
          <p className="hint video-mode-intro">
            <strong>Camera required</strong> — allow camera and microphone to attend this
            step. Grading uses your <strong>spoken words</strong> only, not facial
            analysis.
          </p>
              <div
                className={`video-preview-wrap${!cameraReady ? " video-preview-fallback" : ""}`}
              >
                {!cameraReady ? (
                  <div className="video-preview-fallback-msg" role="status">
                    <strong>Camera not active.</strong>
                    <span>
                      {" "}
                      Allow camera and mic in your browser, fix device settings, then{" "}
                      <strong>Retry camera</strong>. You cannot record until the preview
                      shows your video.
                    </span>
                  </div>
                ) : (
                  <>
                    <video
                      ref={videoPreviewRef}
                      className="video-preview"
                      autoPlay
                      playsInline
                      muted
                      aria-label="Camera preview"
                    />
                    {recording ? (
                      <div className="rec-overlay" aria-live="polite">
                        <span className="rec-dot" aria-hidden="true" />
                        <span>REC — video + voice</span>
                      </div>
                    ) : null}
                  </>
                )}
              </div>
              {!cameraReady && !recording ? (
                <div className="row" style={{ marginBottom: "0.75rem" }}>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => {
                      setError("");
                      setVideoPreviewKey((k) => k + 1);
                    }}
                    disabled={loading}
                  >
                    Retry camera
                  </button>
                </div>
              ) : null}
              <p className="hint video-preview-hint">
                {!cameraReady
                  ? "Use Retry camera after changing permissions or plugging in a webcam."
                  : "You should see yourself above. If it stays black, check permissions (lock icon in the address bar)."}
              </p>
          <div className="row">
            {!recording ? (
              <button
                type="button"
                className="btn btn-primary"
                onClick={startRecording}
                disabled={loading || !cameraReady}
              >
                Answer
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
          {recording ? (
            <p className="hint live-caption-hint" role="status">
              <strong>Voice + video</strong> are recording; your face appears in the
              preview above. <strong>Live transcript is off</strong> while the camera
              uses the mic (browser limit). Your <strong>full transcript</strong> shows
              after you press Stop (Whisper on the server).
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
                ? "Recording video and voice — preview above. Transcript after Stop."
                : cameraReady
                  ? "Press Record, then Stop when you are done (up to 10 minutes)."
                  : "Allow camera and microphone to enable recording."}
          </p>
            </>
          ) : null}
        </div>
      )}

      {step === "results" && result && (
        <div className="card">
          {sessionHistory.length > 0 ? (
            <p className="session-progress">
              Session: <strong>{sessionHistory.length}</strong> answered question
              {sessionHistory.length === 1 ? "" : "s"} recorded — view full report when you
              finish.
            </p>
          ) : null}
          {result._note ? (
            <p className="status" style={{ marginBottom: "1rem" }}>
              {result._note}
            </p>
          ) : null}
          {result.recording_id && result.recording_token ? (
            <div className="saved-recording-block">
              <h3 className="review-block-title">Your saved recording</h3>
              <p className="hint">
                File on server + row in the database (metadata). Keep the token private;
                admins can list clips if <code className="inline-code">ADMIN_API_KEY</code>{" "}
                is set.
              </p>
              {result.recording_media_kind === "video" ? (
                <video
                  key={result.recording_id}
                  className="review-media"
                  src={apiUrl(
                    `/api/recording/${result.recording_id}/media?token=${encodeURIComponent(result.recording_token)}`
                  )}
                  controls
                  playsInline
                />
              ) : (
                <audio
                  key={result.recording_id}
                  className="review-audio"
                  src={apiUrl(
                    `/api/recording/${result.recording_id}/media?token=${encodeURIComponent(result.recording_token)}`
                  )}
                  controls
                />
              )}
            </div>
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

      {step === "summary" && (
        <div className="card summary-card">
          <h2 className="summary-title">Interview session report</h2>
          <p className="summary-meta">
            You completed <strong>{sessionHistory.length}</strong> graded question
            {sessionHistory.length === 1 ? "" : "s"}. Below is each question, your transcript,
            ratings, suggestions, and how to say it better.
          </p>
          <ol className="history-list">
            {sessionHistory.map((item, idx) => (
              <li key={`${item.question_id}-${idx}`} className="history-item">
                <div className="history-head">
                  <span className="history-round">Q{item.round}</span>
                  <span className="history-source">{item.sourceLabel}</span>
                  {item.bank_role_category ? (
                    <span className="history-bank-role">{item.bank_role_category}</span>
                  ) : null}
                  {item.question_kind ? (
                    <span className="history-kind">{item.question_kind}</span>
                  ) : null}
                </div>
                <p className="history-question">{item.question_text}</p>
                {item.note ? (
                  <p className="history-note">{item.note}</p>
                ) : null}
                <h4 className="history-h">Your answer (transcript)</h4>
                <p className="history-transcript">
                  {item.transcript || "—"}
                </p>
                <h4 className="history-h">Ratings (1–5)</h4>
                <div className="scores scores-compact">
                  {["clarity", "correctness", "completeness"].map((k) => (
                    <div key={k} className="score-pill">
                      <span>{item.scores?.[k] ?? "—"}</span>
                      <small>{k}</small>
                    </div>
                  ))}
                </div>
                <h4 className="history-h">Summary</h4>
                <p className="history-p">{item.feedback_summary || "—"}</p>
                <h4 className="history-h">Suggestions for improvement</h4>
                <p className="history-p history-suggestions">
                  {item.suggestions_for_improvement || "—"}
                </p>
                {item.improved_answer_example ? (
                  <>
                    <h4 className="history-h">How to say it better</h4>
                    <p className="improved-sample history-improved">
                      {item.improved_answer_example}
                    </p>
                  </>
                ) : null}
                <h4 className="history-h">Reference answer</h4>
                <div className="perfect history-perfect">{item.perfect_answer || "—"}</div>
              </li>
            ))}
          </ol>
          <div className="row" style={{ marginTop: "1.5rem" }}>
            <button
              type="button"
              className="btn btn-primary"
              onClick={resetSessionToSetup}
            >
              Start over
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
