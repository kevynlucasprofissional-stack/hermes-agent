"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// electron/fixtures/run-electron-learning-proof.ts
var import_node_child_process2 = require("node:child_process");
var import_node_fs2 = __toESM(require("node:fs"), 1);
var import_node_path2 = __toESM(require("node:path"), 1);
var import_electron2 = require("electron");

// electron/workstation-learning-session.ts
var import_node_child_process = require("node:child_process");
var import_node_fs = __toESM(require("node:fs"), 1);
var import_node_path = __toESM(require("node:path"), 1);
var import_electron = require("electron");

// electron/workstation-learning-events.ts
var SENSITIVE = /password|passcode|secret|token|key|credential|authorization|cookie|otp|recovery|private|account|session|api|payment|card|email|address/i;
var allowedRoles = /* @__PURE__ */ new Set(["button", "menuitem", "tab", "checkbox", "radio", "slider", "option", "switch", "link"]);
var allowedKeys = /* @__PURE__ */ new Set(["Enter", "Escape", "Backspace", "Delete", "Tab", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Space", "Home", "End", "PageUp", "PageDown", ..."1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("")]);
function clamp(n) {
  return Math.min(1, Math.max(0, n));
}
function isValidRawGesture(raw) {
  if (!raw.eventId || !raw.tabId || !raw.documentEpoch) {
    return false;
  }
  if (!Number.isFinite(raw.relativeTimeMs) || raw.relativeTimeMs < 0) {
    return false;
  }
  return true;
}
function isEditableTarget(raw) {
  if (raw.isEditable || raw.inputType) {
    return true;
  }
  const tag = raw.elementTag?.toLowerCase();
  return tag === "input" || tag === "textarea";
}
function extractShortcut(raw) {
  if (!(raw.ctrl || raw.meta || raw.alt)) {
    return null;
  }
  const key = raw.key?.length === 1 ? raw.key.toUpperCase() : raw.key;
  if (!key || !allowedKeys.has(key)) {
    return null;
  }
  return [raw.ctrl ? "Ctrl" : null, raw.meta ? "Meta" : null, raw.alt ? "Alt" : null, raw.shift ? "Shift" : null, key].filter(Boolean).join("+");
}
function extractNormalizedPosition(raw) {
  const { x, y, viewportWidth, viewportHeight } = raw;
  if (!Number.isFinite(x) || !Number.isFinite(y)) {
    return void 0;
  }
  if (!Number.isFinite(viewportWidth) || !Number.isFinite(viewportHeight)) {
    return void 0;
  }
  if ((viewportWidth ?? 0) <= 0 || (viewportHeight ?? 0) <= 0) {
    return void 0;
  }
  return {
    x: Math.round(1e3 * clamp((x ?? 0) / (viewportWidth ?? 1))) / 1e3,
    y: Math.round(1e3 * clamp((y ?? 0) / (viewportHeight ?? 1))) / 1e3
  };
}
function extractTarget(raw) {
  const role = raw.role?.toLowerCase().trim() ?? "";
  if (!allowedRoles.has(role)) {
    return void 0;
  }
  const output = { role };
  const name = raw.accessibleName?.trim();
  if (name && name.length <= 80 && !SENSITIVE.test(name)) {
    output.accessible_name = name;
  }
  return output;
}
function normalizeHumanGesture(raw) {
  if (!isValidRawGesture(raw) || isEditableTarget(raw)) {
    return null;
  }
  const output = {
    schema: "hermes.human_gesture.v1",
    event_id: raw.eventId.slice(0, 100),
    browser_tab_id: raw.tabId.slice(0, 100),
    document_epoch: raw.documentEpoch.slice(0, 100),
    time_ms: Math.round(raw.relativeTimeMs),
    kind: raw.kind,
    actor: "human"
  };
  if (raw.kind === "shortcut") {
    const shortcut = extractShortcut(raw);
    if (!shortcut) {
      return null;
    }
    output.shortcut = shortcut;
    return output;
  }
  const pos = extractNormalizedPosition(raw);
  if (pos) {
    output.normalized_position = pos;
  }
  const target = extractTarget(raw);
  if (target) {
    output.target = target;
  }
  return output;
}

// electron/workstation-learning-question-policy.ts
var LEARNING_QUESTION_PRESETS = {
  discreto: { minScore: 0.82, maxQuestionsPerFiveMinutes: 1, maxPending: 2, cooldownMs: 24e4 },
  equilibrado: { minScore: 0.69, maxQuestionsPerFiveMinutes: 2, maxPending: 3, cooldownMs: 105e3 },
  intensivo: { minScore: 0.55, maxQuestionsPerFiveMinutes: 4, maxPending: 5, cooldownMs: 4e4 }
};
var clamp01 = (n) => Number.isFinite(n) ? Math.min(1, Math.max(0, n)) : 0;
function learningQuestionScore(candidate) {
  return Math.round(1e3 * clamp01(
    0.23 * clamp01(candidate.novelty) + 0.25 * clamp01(candidate.uncertainty) + 0.52 * clamp01(candidate.reuseValue) - 0.22 * clamp01(candidate.interruptionCost)
  )) / 1e3;
}
function decideLearningQuestion(candidate, context) {
  const score = learningQuestionScore(candidate);
  if (!candidate.id || !candidate.dedupeKey || !candidate.eventRefs.length) {
    return { action: "observe", score, reason: "no_evidence" };
  }
  if (context.userPausedQuestions) {
    return { action: "observe", score, reason: "paused" };
  }
  if (context.alreadyAskedKeys.has(candidate.dedupeKey)) {
    return { action: "observe", score, reason: "duplicate" };
  }
  const policy = LEARNING_QUESTION_PRESETS[context.intensity];
  if (score < policy.minScore) {
    return { action: "observe", score, reason: "low_information_gain" };
  }
  if (context.pendingQueueSize >= policy.maxPending) {
    return { action: "observe", score, reason: "queue_full" };
  }
  const recent = context.recentlyPresentedAtMs.filter(
    (t) => Number.isFinite(t) && t <= context.nowMs && context.nowMs - t < 3e5
  );
  if (context.userBusy) {
    return { action: "queue", score, reason: "busy" };
  }
  if (recent.length >= policy.maxQuestionsPerFiveMinutes) {
    return { action: "queue", score, reason: "window_budget" };
  }
  const last = recent.length ? Math.max(...recent) : -Infinity;
  if (context.nowMs - last < policy.cooldownMs) {
    return { action: "queue", score, reason: "cooldown" };
  }
  return { action: "ask", score, reason: "opportunity" };
}
function parseLearningIntensity(raw) {
  if (raw === "discreto" || raw === "equilibrado" || raw === "intensivo") {
    return raw;
  }
  throw new Error("unsupported_learning_intensity");
}

// electron/workstation-learning-session.ts
var AUTH_URL_PATTERN = /(login|signin|auth|oauth|account|sso|signup|register|checkout|verify)/i;
function defaultBaseDir() {
  try {
    return import_node_path.default.join(import_electron.app.getPath("userData"), "workstation", "learning-sessions");
  } catch {
    return import_node_path.default.join(process.cwd(), ".hermes-workstation", "learning-sessions");
  }
}
var LearningSessionRecorder = class {
  baseDir;
  captureScreenshot;
  captureFrame;
  capturePage;
  getNowMs;
  ffmpegBin;
  configuredFps;
  configuredFrameIntervalMs;
  state = null;
  activeConfig = null;
  alreadyAskedKeys = /* @__PURE__ */ new Set();
  presentedTimestamps = [];
  questionsMap = /* @__PURE__ */ new Map();
  recentGestures = [];
  videoProcess = null;
  lastEvaluationMs = 0;
  captureTimer = null;
  isCapturing = false;
  sessionStartTimeMs = 0;
  frameCount = 0;
  fps = 3;
  frameIntervalMs = 333;
  lastFrameBuffer = null;
  lastFrameNumber = null;
  lastFrameWidth = 1280;
  lastFrameHeight = 720;
  ffmpegExitCode = null;
  ffmpegErrorOutput = "";
  constructor(options = {}) {
    this.baseDir = options.baseDir || defaultBaseDir();
    this.captureScreenshot = options.captureScreenshot;
    this.captureFrame = options.captureFrame;
    this.capturePage = options.capturePage;
    this.getNowMs = options.nowMs || (() => Date.now());
    this.ffmpegBin = options.ffmpegBin;
    this.configuredFps = options.fps;
    this.configuredFrameIntervalMs = options.frameIntervalMs;
  }
  isActive() {
    return this.state !== null && (this.state.status === "learning" || this.state.status === "paused");
  }
  getStatus() {
    if (!this.state) {
      return null;
    }
    return {
      ...this.state,
      framesCount: this.frameCount,
      pendingQuestions: Array.from(this.questionsMap.values()).filter((q) => q.state === "pending")
    };
  }
  getQuestions() {
    return Array.from(this.questionsMap.values());
  }
  async start(config) {
    if (this.isActive()) {
      throw new Error(`learning_session_already_active:${this.state?.sessionId}`);
    }
    const intensity = parseLearningIntensity(config.intensity ?? "intensivo");
    const sessionId = `learn-${Date.now()}-${config.tabId.slice(0, 8)}`;
    const sessionDir = import_node_path.default.join(this.baseDir, sessionId);
    const snapshotsDir = import_node_path.default.join(sessionDir, "snapshots");
    const mediaDir = import_node_path.default.join(sessionDir, "media");
    import_node_fs.default.mkdirSync(sessionDir, { recursive: true });
    import_node_fs.default.mkdirSync(snapshotsDir, { recursive: true });
    import_node_fs.default.mkdirSync(mediaDir, { recursive: true });
    const eventsPath = import_node_path.default.join(sessionDir, "events.jsonl");
    const questionsPath = import_node_path.default.join(sessionDir, "questions.jsonl");
    const frameIndexPath = import_node_path.default.join(mediaDir, "frame_index.jsonl");
    if (!import_node_fs.default.existsSync(eventsPath)) {
      import_node_fs.default.writeFileSync(eventsPath, "", { encoding: "utf-8" });
    }
    if (!import_node_fs.default.existsSync(questionsPath)) {
      import_node_fs.default.writeFileSync(questionsPath, "", { encoding: "utf-8" });
    }
    if (!import_node_fs.default.existsSync(frameIndexPath)) {
      import_node_fs.default.writeFileSync(frameIndexPath, "", { encoding: "utf-8" });
    }
    this.alreadyAskedKeys.clear();
    this.presentedTimestamps = [];
    this.questionsMap.clear();
    this.recentGestures = [];
    this.lastEvaluationMs = this.getNowMs();
    this.activeConfig = config;
    this.fps = config.fps || this.configuredFps || 3;
    this.frameIntervalMs = config.frameIntervalMs || this.configuredFrameIntervalMs || Math.max(50, Math.round(1e3 / this.fps));
    this.sessionStartTimeMs = this.getNowMs();
    this.frameCount = 0;
    this.lastFrameBuffer = null;
    this.lastFrameNumber = null;
    this.lastFrameWidth = 1280;
    this.lastFrameHeight = 720;
    this.isCapturing = false;
    let videoStatus = "disabled";
    if (config.videoEnabled !== false) {
      videoStatus = this.startVideoRecording(mediaDir);
    }
    this.state = {
      schema: "hermes.learning_session.v1",
      sessionId,
      runtimeSessionId: config.runtimeSessionId,
      storedSessionId: config.storedSessionId,
      tabId: config.tabId,
      webContentsId: config.webContentsId,
      documentEpoch: config.documentEpoch,
      status: "learning",
      intensity,
      startedAt: (/* @__PURE__ */ new Date()).toISOString(),
      endedAt: null,
      allowlistedOrigin: config.allowlistedOrigin,
      eventsCount: 0,
      questionsCount: 0,
      framesCount: 0,
      pendingQuestions: [],
      videoStatus,
      lastError: null,
      sessionDir,
      userBusy: false
    };
    this.persistManifest();
    if (videoStatus === "recording") {
      this.scheduleNextCapture(0);
    }
    return this.getStatus();
  }
  async setIntensity(rawIntensity) {
    if (!this.state || !this.isActive()) {
      throw new Error("no_active_learning_session");
    }
    const newIntensity = parseLearningIntensity(rawIntensity);
    if (this.state.intensity === newIntensity) {
      return this.getStatus();
    }
    this.state.intensity = newIntensity;
    this.persistManifest();
    await this.evaluateQuestions();
    return this.getStatus();
  }
  checkNavigation(targetUrl) {
    if (!this.state || !this.isActive()) {
      return true;
    }
    try {
      const urlObj = new URL(targetUrl);
      if (AUTH_URL_PATTERN.test(urlObj.pathname) || AUTH_URL_PATTERN.test(urlObj.hostname)) {
        this.pause(`Auth/login page detected: ${urlObj.origin}${urlObj.pathname}. Paused before capturing frames.`);
        return false;
      }
      if (this.state.allowlistedOrigin) {
        const allowed = new URL(this.state.allowlistedOrigin);
        if (urlObj.origin !== allowed.origin) {
          this.pause(`Off-origin navigation: ${urlObj.origin} !== ${allowed.origin}. Paused before capturing frames.`);
          return false;
        }
      }
      return true;
    } catch {
      this.pause(`Invalid or unparseable target navigation: ${targetUrl}`);
      return false;
    }
  }
  pause(reason) {
    if (!this.state) {
      throw new Error("no_learning_session");
    }
    this.state.status = "paused";
    if (this.captureTimer) {
      clearTimeout(this.captureTimer);
      this.captureTimer = null;
    }
    if (reason) {
      this.state.lastError = reason;
    }
    this.persistManifest();
    return this.getStatus();
  }
  resume() {
    if (!this.state) {
      throw new Error("no_learning_session");
    }
    this.state.status = "learning";
    this.state.lastError = null;
    this.persistManifest();
    if (this.state.videoStatus === "recording") {
      this.scheduleNextCapture(0);
    }
    return this.getStatus();
  }
  setUserBusy(busy) {
    if (this.state) {
      this.state.userBusy = busy;
    }
  }
  async recordGesture(raw) {
    if (!this.state || this.state.status !== "learning") {
      return null;
    }
    const safe = normalizeHumanGesture(raw);
    if (!safe) {
      return null;
    }
    if (this.lastFrameNumber !== null) {
      safe.frame_number = this.lastFrameNumber;
    }
    if (safe.kind === "pointerdown") {
      this.setUserBusy(true);
    } else if (safe.kind === "pointerup") {
      this.setUserBusy(false);
    }
    if (safe.kind === "click" || safe.kind === "shortcut") {
      const snapFilename = `snap_${safe.event_id}_${safe.time_ms}.png`;
      const snapRelPath = import_node_path.default.join("snapshots", snapFilename).replace(/\\/g, "/");
      const snapAbsPath = import_node_path.default.join(this.state.sessionDir, "snapshots", snapFilename);
      if (this.lastFrameBuffer) {
        try {
          import_node_fs.default.writeFileSync(snapAbsPath, this.lastFrameBuffer);
          safe.snapshot_ref = snapRelPath;
        } catch {
        }
      } else if (this.captureScreenshot) {
        try {
          const res = await this.captureScreenshot(this.state.tabId, snapAbsPath);
          if (res && res.success) {
            safe.snapshot_ref = snapRelPath;
          }
        } catch {
        }
      }
    }
    try {
      const eventsPath = import_node_path.default.join(this.state.sessionDir, "events.jsonl");
      import_node_fs.default.appendFileSync(eventsPath, JSON.stringify(safe) + "\n", "utf-8");
    } catch {
    }
    this.state.eventsCount++;
    this.recentGestures.push(safe);
    if (this.recentGestures.length > 50) {
      this.recentGestures.shift();
    }
    this.persistManifest();
    await this.evaluateQuestions();
    return safe;
  }
  async evaluateQuestions() {
    if (!this.state || this.state.status !== "learning") {
      return [];
    }
    if (this.recentGestures.length === 0) {
      return [];
    }
    const now = this.getNowMs();
    const lastGesture = this.recentGestures[this.recentGestures.length - 1];
    const candidate = this.generateCandidate(lastGesture, now);
    if (!candidate) {
      return this.getStatus()?.pendingQuestions || [];
    }
    const context = {
      intensity: this.state.intensity,
      nowMs: now,
      recentlyPresentedAtMs: this.presentedTimestamps,
      pendingQueueSize: Array.from(this.questionsMap.values()).filter((q) => q.state === "pending").length,
      alreadyAskedKeys: this.alreadyAskedKeys,
      userBusy: this.state.userBusy,
      userPausedQuestions: false
    };
    const decision = decideLearningQuestion(candidate.policyCandidate, context);
    if (decision.action === "ask") {
      const questionItem = {
        id: `q-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        sessionId: this.state.sessionId,
        tabId: this.state.tabId,
        eventRefs: [...candidate.policyCandidate.eventRefs],
        fromMs: lastGesture.time_ms,
        toMs: lastGesture.time_ms,
        kind: candidate.policyCandidate.kind,
        category: candidate.category,
        hypothesis: candidate.hypothesis,
        uncertainty: candidate.policyCandidate.uncertainty,
        score: decision.score,
        dedupeKey: candidate.policyCandidate.dedupeKey,
        proposedQuestion: candidate.proposedQuestion,
        state: "pending",
        needsReinterpretation: false,
        createdAt: (/* @__PURE__ */ new Date()).toISOString()
      };
      this.questionsMap.set(questionItem.id, questionItem);
      this.alreadyAskedKeys.add(questionItem.dedupeKey);
      this.presentedTimestamps.push(now);
      this.state.questionsCount++;
      try {
        const questionsPath = import_node_path.default.join(this.state.sessionDir, "questions.jsonl");
        import_node_fs.default.appendFileSync(questionsPath, JSON.stringify(questionItem) + "\n", "utf-8");
      } catch {
      }
      this.persistManifest();
    }
    return Array.from(this.questionsMap.values()).filter((q) => q.state === "pending");
  }
  async answerQuestion(questionId, input) {
    if (!this.state) {
      throw new Error("no_learning_session");
    }
    const question = this.questionsMap.get(questionId);
    if (!question) {
      throw new Error(`question_not_found:${questionId}`);
    }
    const actionMap = {
      confirm: "confirmed",
      correct: "corrected",
      defer: "deferred",
      dismiss: "dismissed"
    };
    question.state = actionMap[input.action];
    question.answeredAt = (/* @__PURE__ */ new Date()).toISOString();
    if (input.action === "confirm") {
      question.userResponse = "Confirmed by user";
      question.needsReinterpretation = false;
    } else if (input.action === "correct") {
      question.userResponse = input.userCorrection || "Corrected by user";
      question.needsReinterpretation = true;
    } else if (input.action === "defer") {
      question.userResponse = "Deferred";
    } else if (input.action === "dismiss") {
      question.userResponse = "Dismissed";
    }
    try {
      const questionsPath = import_node_path.default.join(this.state.sessionDir, "questions.jsonl");
      import_node_fs.default.appendFileSync(questionsPath, JSON.stringify(question) + "\n", "utf-8");
    } catch {
    }
    this.persistManifest();
    return question;
  }
  async stop() {
    if (!this.state || this.state.status === "idle") {
      return this.state || {
        schema: "hermes.learning_session.v1",
        sessionId: "",
        runtimeSessionId: "",
        storedSessionId: "",
        tabId: "",
        webContentsId: 0,
        documentEpoch: "",
        status: "idle",
        intensity: "intensivo",
        startedAt: "",
        endedAt: null,
        allowlistedOrigin: "",
        eventsCount: 0,
        questionsCount: 0,
        framesCount: 0,
        pendingQuestions: [],
        videoStatus: "stopped",
        lastError: null,
        sessionDir: "",
        userBusy: false
      };
    }
    if (this.captureTimer) {
      clearTimeout(this.captureTimer);
      this.captureTimer = null;
    }
    while (this.isCapturing) {
      await new Promise((resolve) => setTimeout(resolve, 20));
    }
    await this.stopVideoRecording();
    this.state.status = "idle";
    this.state.endedAt = (/* @__PURE__ */ new Date()).toISOString();
    this.persistManifest();
    const finalState = this.getStatus();
    this.state = null;
    this.activeConfig = null;
    return finalState;
  }
  async discard() {
    if (!this.state) {
      return;
    }
    const sessionDir = this.state.sessionDir;
    if (this.captureTimer) {
      clearTimeout(this.captureTimer);
      this.captureTimer = null;
    }
    if (this.videoProcess) {
      try {
        this.videoProcess.kill("SIGKILL");
      } catch {
      }
      this.videoProcess = null;
    }
    this.state = null;
    this.activeConfig = null;
    this.questionsMap.clear();
    this.alreadyAskedKeys.clear();
    this.lastFrameBuffer = null;
    this.lastFrameNumber = null;
    this.frameCount = 0;
    try {
      if (import_node_fs.default.existsSync(sessionDir)) {
        import_node_fs.default.rmSync(sessionDir, { recursive: true, force: true });
      }
    } catch {
    }
  }
  generateCandidate(gesture, nowMs) {
    if (gesture.kind === "shortcut" && gesture.shortcut) {
      const dedupeKey = `shortcut:${gesture.shortcut}`;
      return {
        policyCandidate: {
          id: `cand-${gesture.event_id}`,
          dedupeKey,
          kind: "causality",
          eventRefs: [gesture.event_id],
          novelty: 0.85,
          uncertainty: 0.8,
          reuseValue: 0.95,
          interruptionCost: 0.1
        },
        category: "causality",
        hypothesis: `O operador utilizou o atalho ${gesture.shortcut} como passo deliberado de controle ou sincroniza\xE7\xE3o.`,
        proposedQuestion: `Por que voc\xEA executou o atalho ${gesture.shortcut} nesta etapa da demonstra\xE7\xE3o?`
      };
    }
    if (gesture.kind === "click" && gesture.target?.role) {
      const name = gesture.target.accessible_name || gesture.target.role;
      const dedupeKey = `click:${gesture.target.role}:${name}`;
      return {
        policyCandidate: {
          id: `cand-${gesture.event_id}`,
          dedupeKey,
          kind: "decision",
          eventRefs: [gesture.event_id],
          novelty: 0.75,
          uncertainty: 0.75,
          reuseValue: 0.85,
          interruptionCost: 0.15
        },
        category: "decision",
        hypothesis: `O operador selecionou '${name}' com base em um crit\xE9rio espec\xEDfico do projeto ou fluxo de edi\xE7\xE3o.`,
        proposedQuestion: `Qual foi o crit\xE9rio para escolher '${name}' nesta etapa?`
      };
    }
    if (gesture.kind === "pointerup" && gesture.normalized_position) {
      const pos = gesture.normalized_position;
      const dedupeKey = `canvas:pointer:${Math.floor(pos.x * 10)}_${Math.floor(pos.y * 10)}`;
      return {
        policyCandidate: {
          id: `cand-${gesture.event_id}`,
          dedupeKey,
          kind: "heuristic",
          eventRefs: [gesture.event_id],
          novelty: 0.7,
          uncertainty: 0.85,
          reuseValue: 0.8,
          interruptionCost: 0.2
        },
        category: "heuristic",
        hypothesis: `O operador manipulou a \xE1rea do Canvas nas coordenadas normalizadas (${pos.x}, ${pos.y}).`,
        proposedQuestion: `Qual ajuste visual ou par\xE2metro voc\xEA refinou nesta \xE1rea do Canvas?`
      };
    }
    return null;
  }
  startVideoRecording(mediaDir) {
    try {
      const videoPath = import_node_path.default.join(mediaDir, "recording.webm");
      const ffmpegBin = this.ffmpegBin || (process.platform === "win32" ? "ffmpeg.exe" : "ffmpeg");
      const ffmpegArgs = [
        "-y",
        "-f",
        "image2pipe",
        "-framerate",
        String(this.fps),
        "-vcodec",
        "png",
        "-i",
        "pipe:0",
        "-an",
        "-c:v",
        "libvpx-vp9",
        "-deadline",
        "realtime",
        "-cpu-used",
        "5",
        "-pix_fmt",
        "yuv420p",
        videoPath
      ];
      this.ffmpegExitCode = null;
      this.ffmpegErrorOutput = "";
      const proc = (0, import_node_child_process.spawn)(ffmpegBin, ffmpegArgs, {
        stdio: ["pipe", "ignore", "pipe"]
      });
      proc.on("error", (err) => {
        this.ffmpegExitCode = -1;
        if (this.state) {
          this.state.videoStatus = "blocked";
          this.state.lastError = `ffmpeg_unavailable: ${err.message}`;
          this.persistManifest();
        }
      });
      proc.stderr?.on("data", (chunk) => {
        this.ffmpegErrorOutput = (this.ffmpegErrorOutput + chunk.toString()).slice(-4096);
      });
      proc.stdin?.on("error", () => {
      });
      proc.on("close", (code) => {
        this.ffmpegExitCode = code;
        if (this.state && this.state.status === "learning" && code !== 0 && this.state.videoStatus !== "blocked") {
          this.state.videoStatus = "error";
          this.state.lastError = `ffmpeg_crashed: exit code ${code}. ${this.ffmpegErrorOutput}`;
          this.persistManifest();
        }
      });
      this.videoProcess = proc;
      return "recording";
    } catch (err) {
      return "blocked";
    }
  }
  scheduleNextCapture(delayMs = this.frameIntervalMs) {
    if (!this.state || this.state.status !== "learning") {
      return;
    }
    if (this.captureTimer) {
      clearTimeout(this.captureTimer);
      this.captureTimer = null;
    }
    this.captureTimer = setTimeout(() => {
      void this.captureAndProcessFrame();
    }, delayMs);
  }
  async captureAndProcessFrame() {
    if (!this.state || this.state.status !== "learning") {
      return;
    }
    if (this.isCapturing) {
      this.scheduleNextCapture();
      return;
    }
    this.isCapturing = true;
    try {
      if (!this.videoProcess || !this.videoProcess.stdin || this.videoProcess.stdin.destroyed) {
        return;
      }
      const tabId = this.state.tabId;
      const captureFn = this.activeConfig?.captureFrame || this.captureFrame || (this.capturePage ? async (id) => {
        const buf = await this.capturePage(id);
        return buf ? { buffer: buf, width: 1280, height: 720 } : null;
      } : null);
      if (!captureFn) {
        return;
      }
      const captureResult = await captureFn(tabId);
      if (!captureResult) {
        return;
      }
      if (!this.state || this.state.status !== "learning") {
        return;
      }
      const buffer = Buffer.isBuffer(captureResult) ? captureResult : captureResult.buffer;
      const width = Buffer.isBuffer(captureResult) ? 1280 : captureResult.width || 1280;
      const height = Buffer.isBuffer(captureResult) ? 720 : captureResult.height || 720;
      if (!buffer || buffer.length === 0) {
        return;
      }
      const stdin = this.videoProcess.stdin;
      if (stdin.destroyed) {
        return;
      }
      const currentFrameNumber = this.frameCount;
      const now = this.getNowMs();
      const ptsMs = Math.round(currentFrameNumber * 1e3 / this.fps);
      const relativeMs = now - this.sessionStartTimeMs;
      const ok = stdin.write(buffer);
      const frameRecord = {
        frame_number: currentFrameNumber,
        timestamp_ms: now,
        pts_ms: ptsMs,
        relative_ms: relativeMs,
        duration_ms: this.frameIntervalMs,
        width,
        height,
        bytes: buffer.length
      };
      try {
        const frameIndexPath = import_node_path.default.join(this.state.sessionDir, "media", "frame_index.jsonl");
        import_node_fs.default.appendFileSync(frameIndexPath, JSON.stringify(frameRecord) + "\n", "utf-8");
      } catch {
      }
      this.frameCount++;
      this.lastFrameBuffer = buffer;
      this.lastFrameNumber = currentFrameNumber;
      this.lastFrameWidth = width;
      this.lastFrameHeight = height;
      if (this.state) {
        this.state.framesCount = this.frameCount;
      }
      if (!ok) {
        await new Promise((resolve) => {
          const onDrain = () => {
            stdin.removeListener("error", onError);
            resolve();
          };
          const onError = () => {
            stdin.removeListener("drain", onDrain);
            resolve();
          };
          stdin.once("drain", onDrain);
          stdin.once("error", onError);
        });
      }
    } catch {
    } finally {
      this.isCapturing = false;
      this.scheduleNextCapture();
    }
  }
  async stopVideoRecording() {
    if (!this.videoProcess) {
      if (this.state && this.state.videoStatus === "recording") {
        this.state.videoStatus = "stopped";
      }
      return;
    }
    const proc = this.videoProcess;
    this.videoProcess = null;
    if (proc.stdin && !proc.stdin.destroyed) {
      await new Promise((resolve) => {
        try {
          proc.stdin.end(() => resolve());
        } catch {
          resolve();
        }
      });
    }
    await new Promise((resolve) => {
      if (proc.exitCode !== null || proc.killed) {
        this.ffmpegExitCode = proc.exitCode;
        resolve();
        return;
      }
      let finished = false;
      const timer = setTimeout(() => {
        if (!finished) {
          finished = true;
          try {
            proc.kill("SIGKILL");
          } catch {
          }
          resolve();
        }
      }, 1e4);
      proc.once("close", (code) => {
        clearTimeout(timer);
        if (!finished) {
          finished = true;
          this.ffmpegExitCode = code;
          resolve();
        }
      });
    });
    if (!this.state) {
      return;
    }
    if (this.state.videoStatus === "blocked") {
      return;
    }
    const videoPath = import_node_path.default.join(this.state.sessionDir, "media", "recording.webm");
    if (!import_node_fs.default.existsSync(videoPath)) {
      this.state.videoStatus = "error";
      this.state.lastError = "video_file_missing: recording.webm was not created";
      return;
    }
    const stat = import_node_fs.default.statSync(videoPath);
    if (stat.size <= 0) {
      this.state.videoStatus = "error";
      this.state.lastError = "video_file_empty: recording.webm is empty (0 bytes)";
      return;
    }
    if (this.frameCount === 0) {
      this.state.videoStatus = "error";
      this.state.lastError = "no_frames_recorded: 0 frames were fed to the encoder";
      return;
    }
    if (this.ffmpegExitCode !== null && this.ffmpegExitCode !== 0) {
      this.state.videoStatus = "error";
      this.state.lastError = `ffmpeg_exit_error: exit code ${this.ffmpegExitCode}. ${this.ffmpegErrorOutput}`;
      return;
    }
    this.state.videoStatus = "stopped";
  }
  persistManifest() {
    if (!this.state) {
      return;
    }
    try {
      const sessionFile = import_node_path.default.join(this.state.sessionDir, "learning_session.json");
      import_node_fs.default.writeFileSync(sessionFile, JSON.stringify(this.state, null, 2), "utf-8");
    } catch {
    }
  }
};

// electron/fixtures/run-electron-learning-proof.ts
async function run() {
  console.log("[proof] Starting real Electron visual demonstration capture...");
  const fixturePath = import_node_path2.default.join(__dirname, "visual-demonstration-fixture.html");
  if (!import_node_fs2.default.existsSync(fixturePath)) {
    throw new Error(`Fixture not found: ${fixturePath}`);
  }
  const outputDir = import_node_path2.default.join(import_electron2.app.getPath("userData"), "real-electron-learning-proof");
  import_node_fs2.default.rmSync(outputDir, { recursive: true, force: true });
  import_node_fs2.default.mkdirSync(outputDir, { recursive: true });
  const win = new import_electron2.BrowserWindow({
    width: 1280,
    height: 720,
    show: false,
    webPreferences: {
      offscreen: false,
      contextIsolation: true
    }
  });
  await win.loadFile(fixturePath);
  console.log("[proof] Loaded visual-demonstration-fixture.html into BrowserWindow");
  await new Promise((r) => setTimeout(r, 500));
  const recorder = new LearningSessionRecorder({
    baseDir: outputDir,
    fps: 3,
    frameIntervalMs: 250,
    // capture 4 fps to stdin for smooth proof
    captureFrame: async () => {
      if (win.isDestroyed() || win.webContents.isDestroyed()) {
        return null;
      }
      const nativeImage = await win.webContents.capturePage();
      if (!nativeImage || nativeImage.isEmpty()) {
        return null;
      }
      const size = nativeImage.getSize();
      const targetWidth = 1280;
      const targetHeight = 720;
      const resized = size.width === targetWidth && size.height === targetHeight ? nativeImage : nativeImage.resize({ width: targetWidth, height: targetHeight, quality: "good" });
      return {
        buffer: resized.toPNG(),
        width: targetWidth,
        height: targetHeight
      };
    },
    captureScreenshot: async (_tabId, targetPath) => {
      if (win.isDestroyed()) {
        return { success: false };
      }
      const nativeImage = await win.webContents.capturePage();
      const dest = targetPath || import_node_path2.default.join(outputDir, `snap-${Date.now()}.png`);
      import_node_fs2.default.mkdirSync(import_node_path2.default.dirname(dest), { recursive: true });
      import_node_fs2.default.writeFileSync(dest, nativeImage.toPNG());
      return { success: true, screenshot_path: dest };
    }
  });
  const startState = await recorder.start({
    runtimeSessionId: "sess-electron-native-proof",
    storedSessionId: "st-electron-native-proof",
    tabId: "tab-electron-native",
    webContentsId: win.webContents.id,
    documentEpoch: "epoch-real-electron",
    allowlistedOrigin: "file://",
    videoEnabled: true,
    fps: 3,
    frameIntervalMs: 250
  });
  console.log("[proof] Recording active in session:", startState.sessionId);
  for (let step = 1; step <= 5; step++) {
    await new Promise((r) => setTimeout(r, 600));
    if (step === 2) {
      await win.webContents.executeJavaScript(`document.getElementById('btn-color').click()`);
    } else if (step === 3) {
      await win.webContents.executeJavaScript(`document.getElementById('btn-shape').click()`);
    } else if (step === 4) {
      await win.webContents.executeJavaScript(`document.getElementById('btn-save').click()`);
    }
    await recorder.recordGesture({
      eventId: `evt-step-${step}`,
      tabId: "tab-electron-native",
      documentEpoch: "epoch-real-electron",
      relativeTimeMs: step * 600,
      kind: step === 3 ? "shortcut" : "click",
      x: 300 + step * 20,
      y: 200 + step * 10,
      viewportWidth: 1280,
      viewportHeight: 720,
      role: "button",
      accessibleName: step === 3 ? void 0 : `Operator Action ${step}`,
      elementTag: "button",
      key: step === 3 ? "S" : void 0,
      ctrl: step === 3 ? true : void 0
    });
    console.log(`[proof] Step ${step}/5 recorded. Frames: ${recorder.getStatus()?.framesCount}`);
  }
  console.log("[proof] Stopping recording and flushing FFmpeg container...");
  const finalState = await recorder.stop();
  const videoPath = import_node_path2.default.join(finalState.sessionDir, "media", "recording.webm");
  const frameIndexPath = import_node_path2.default.join(finalState.sessionDir, "media", "frame_index.jsonl");
  const snapshotsDir = import_node_path2.default.join(finalState.sessionDir, "snapshots");
  const probeRaw = (0, import_node_child_process2.execSync)(
    `ffprobe -v quiet -print_format json -show_format -show_streams "${videoPath}"`,
    { encoding: "utf-8" }
  );
  const probe = JSON.parse(probeRaw);
  const videoStream = probe.streams.find((s) => s.codec_type === "video");
  const stat = import_node_fs2.default.statSync(videoPath);
  const frameLines = import_node_fs2.default.readFileSync(frameIndexPath, "utf-8").trim().split("\n");
  const snapshots = import_node_fs2.default.readdirSync(snapshotsDir);
  const proofReport = {
    timestamp: (/* @__PURE__ */ new Date()).toISOString(),
    electronVersion: process.versions.electron,
    chromeVersion: process.versions.chrome,
    session: {
      sessionId: finalState.sessionId,
      videoStatus: finalState.videoStatus,
      framesRecorded: finalState.framesCount,
      eventsRecorded: finalState.eventsCount
    },
    video: {
      path: videoPath,
      fileSizeBytes: stat.size,
      codec: videoStream?.codec_name,
      pixelFormat: videoStream?.pix_fmt,
      width: videoStream?.width,
      height: videoStream?.height,
      durationSeconds: Number.parseFloat(probe.format?.duration || "0"),
      container: probe.format?.format_name
    },
    frameIndex: {
      count: frameLines.length,
      sampleFrame0: JSON.parse(frameLines[0] || "{}")
    },
    snapshots: {
      count: snapshots.length,
      files: snapshots
    },
    verificationPassed: finalState.videoStatus === "stopped" && stat.size > 5e3 && videoStream?.codec_name === "vp9" && snapshots.length >= 4
  };
  const proofFile = import_node_path2.default.join(__dirname, "real-electron-recording-proof.json");
  import_node_fs2.default.writeFileSync(proofFile, JSON.stringify(proofReport, null, 2), "utf-8");
  console.log("[proof] SUCCESS! Proof report generated at:", proofFile);
  console.log(JSON.stringify(proofReport, null, 2));
  win.destroy();
  import_electron2.app.quit();
}
import_electron2.app.whenReady().then(run).catch((err) => {
  console.error("[proof] ERROR during real Electron proof:", err);
  import_electron2.app.exit(1);
});
