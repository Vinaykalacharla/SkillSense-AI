import { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  Camera,
  MessageSquare,
  Mic,
  MicOff,
  ShieldAlert,
  Sparkles,
  Square,
  Target,
  TrendingUp,
  Volume2,
  VolumeX,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { buildApiUrl } from '@/lib/api';

interface TranscriptItem {
  speaker: string;
  text: string;
}

interface FeedbackItem {
  type: 'strength' | 'improvement';
  text: string;
}

interface MetricItem {
  label: string;
  value: number;
  color: 'primary' | 'accent';
}

interface InterviewState {
  total_questions?: number;
  current_index?: number;
  current_question?: string | null;
  current_difficulty?: string | null;
  score?: number;
}

type SpeechRecognitionInstance = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  onresult: ((event: any) => void) | null;
  onerror: ((event: any) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
};

const statusStyles = {
  idle: 'border-border/60 bg-muted/40 text-muted-foreground',
  active: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500',
  completed: 'border-primary/30 bg-primary/10 text-primary',
};

export default function AIInterview() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const ttsEnabledRef = useRef(true);
  const autoEndedRef = useRef(false);
  const autoStartedRef = useRef(false);
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null);
  const finalTranscriptRef = useRef('');
  const lastTranscriptRef = useRef('');
  const silenceTimerRef = useRef<number | null>(null);
  const silenceMs = 2000;
  const timerRef = useRef<number | null>(null);
  const answerTimeSec = 90;
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [metrics, setMetrics] = useState<MetricItem[]>([]);
  const [tips, setTips] = useState<string[]>([]);
  const [status, setStatus] = useState<'idle' | 'active' | 'completed'>('idle');
  const [interviewState, setInterviewState] = useState<InterviewState>({});
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const [cameraEnabled, setCameraEnabled] = useState(false);
  const [cameraError, setCameraError] = useState('');
  const [micEnabled, setMicEnabled] = useState(true);
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const [listening, setListening] = useState(false);
  const [liveTranscript, setLiveTranscript] = useState('');
  const [speechSupported, setSpeechSupported] = useState(true);
  const [focusWarnings, setFocusWarnings] = useState(0);
  const [focusMessage, setFocusMessage] = useState('');
  const [secondsLeft, setSecondsLeft] = useState(answerTimeSec);
  const maxWarnings = 2;

  ttsEnabledRef.current = ttsEnabled;

  const startCamera = async () => {
    if (streamRef.current || cameraEnabled) {
      return;
    }
    setCameraError('');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setCameraEnabled(true);
    } catch (err) {
      setCameraError('Camera/mic access was blocked. Please allow access to continue.');
      setCameraEnabled(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
    }
    streamRef.current = null;
    setCameraEnabled(false);
  };

  const initSpeechRecognition = () => {
    const SpeechRecognitionConstructor =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognitionConstructor) {
      setSpeechSupported(false);
      return;
    }
    const recognition = new SpeechRecognitionConstructor() as SpeechRecognitionInstance;
    recognition.lang = 'en-US';
    recognition.interimResults = true;
    recognition.continuous = true;
    recognition.onresult = (event: any) => {
      let interim = '';
      let finalChunk = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const segment = result[0]?.transcript ?? '';
        if (result.isFinal) {
          finalChunk += segment;
        } else {
          interim += segment;
        }
      }
      if (finalChunk) {
        finalTranscriptRef.current = `${finalTranscriptRef.current} ${finalChunk}`.trim();
      }
      const combined = `${finalTranscriptRef.current} ${interim}`.trim();
      setLiveTranscript(combined);
      if (combined && combined !== lastTranscriptRef.current) {
        lastTranscriptRef.current = combined;
        scheduleAutoSend();
      }
    };
    recognition.onerror = () => {
      setError('Voice capture failed. Please retry.');
      setListening(false);
      clearSilenceTimer();
    };
    recognition.onend = () => {
      setListening(false);
      clearSilenceTimer();
    };
    recognitionRef.current = recognition;
  };

  const clearSilenceTimer = () => {
    if (silenceTimerRef.current) {
      window.clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
  };

  const scheduleAutoSend = () => {
    clearSilenceTimer();
    silenceTimerRef.current = window.setTimeout(() => {
      stopListening(true);
    }, silenceMs);
  };

  const startListening = async () => {
    if (!speechSupported) {
      setError('Speech recognition is not supported in this browser.');
      return;
    }
    if (!micEnabled) {
      setError('Turn on the mic to start speaking.');
      return;
    }
    if (!recognitionRef.current) {
      initSpeechRecognition();
    }
    if (!recognitionRef.current) {
      setError('Speech recognition is unavailable.');
      return;
    }
    setError('');
    finalTranscriptRef.current = '';
    lastTranscriptRef.current = '';
    setLiveTranscript('');
    await startCamera();
    try {
      setListening(true);
      scheduleAutoSend();
      recognitionRef.current.start();
    } catch (err) {
      setError('Unable to start voice capture. Please retry.');
      setListening(false);
    }
  };

  const stopListening = async (autoSend = true) => {
    if (!recognitionRef.current) {
      return;
    }
    recognitionRef.current.stop();
    setListening(false);
    clearSilenceTimer();
    const finalText = liveTranscript.trim();
    if (finalText && autoSend) {
      await handleAction('respond', finalText);
      setLiveTranscript('');
      finalTranscriptRef.current = '';
      lastTranscriptRef.current = '';
    }
  };

  const clearAnswerTimer = () => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
      timerRef.current = null;
    }
  };

  const applyInterviewData = (
    data: InterviewState & {
      status?: 'idle' | 'active' | 'completed';
      transcript?: TranscriptItem[];
      feedback?: FeedbackItem[];
      metrics?: MetricItem[];
      tips?: string[];
    },
  ) => {
    if (data?.status) {
      setStatus(data.status);
    }
    setTranscript(Array.isArray(data?.transcript) ? data.transcript : []);
    setFeedback(Array.isArray(data?.feedback) ? data.feedback : []);
    setMetrics(Array.isArray(data?.metrics) ? data.metrics : []);
    setTips(Array.isArray(data?.tips) ? data.tips : []);
    setInterviewState({
      total_questions: data?.total_questions,
      current_index: data?.current_index,
      current_question: data?.current_question,
      current_difficulty: data?.current_difficulty,
      score: data?.score,
    });
  };

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setError('Login required to start the interview.');
      return;
    }
    fetch(buildApiUrl('/api/skills/ai-interview/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        setError('');
        applyInterviewData(data);
      })
      .catch(() => {
        setError('Unable to load interview session. Please try again.');
        setTranscript([]);
        setFeedback([]);
        setMetrics([]);
        setTips([]);
        setInterviewState({});
      });
  }, []);

  useEffect(() => {
    if (status === 'idle' && !autoStartedRef.current) {
      autoStartedRef.current = true;
      handleAction('start');
    }
  }, [status]);

  useEffect(() => {
    initSpeechRecognition();
  }, []);

  const handleAction = async (action: 'start' | 'respond' | 'finish', overrideMessage?: string) => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setError('Login required to start the interview.');
      return;
    }
    const message = (overrideMessage ?? '').trim();
    if (action === 'respond' && !message) {
      return;
    }
    setSending(true);
    try {
      const res = await fetch(buildApiUrl('/api/skills/ai-interview/action/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          action,
          message,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.error || 'Interview action failed. Please try again.');
        return;
      }
      setError('');
      applyInterviewData(data);
    } finally {
      setSending(false);
    }
  };

  const requestFullscreen = async () => {
    if (!document.fullscreenElement) {
      try {
        await document.documentElement.requestFullscreen();
      } catch (err) {
        // Fullscreen is optional; ignore errors.
      }
    }
  };

  const exitFullscreen = async () => {
    if (document.fullscreenElement) {
      try {
        await document.exitFullscreen();
      } catch (err) {
        // Ignore exit errors.
      }
    }
  };

  const totalQuestions = interviewState.total_questions ?? 0;
  const currentIndex = interviewState.current_index ?? 0;
  const currentQuestion = interviewState.current_question ?? '';
  const currentDifficulty = interviewState.current_difficulty ?? '';
  const score = interviewState.score ?? 0;

  const progress = useMemo(() => {
    if (!totalQuestions) {
      return 0;
    }
    const completedOffset = status === 'completed' ? 1 : 0;
    const position = Math.min(currentIndex + completedOffset, totalQuestions);
    return Math.min(100, Math.round((position / totalQuestions) * 100));
  }, [currentIndex, status, totalQuestions]);

  const statusLabel =
    status === 'active' ? 'Live session' : status === 'completed' ? 'Session completed' : 'Ready';

  useEffect(() => {
    if (status === 'active') {
      startCamera();
      requestFullscreen();
    } else {
      exitFullscreen();
    }
    if (status !== 'active') {
      if (listening) {
        stopListening(false);
      }
      clearAnswerTimer();
      setSecondsLeft(answerTimeSec);
      autoEndedRef.current = false;
      setFocusWarnings(0);
      setFocusMessage('');
    }
  }, [status, listening]);

  useEffect(() => {
    if (status !== 'active') {
      return;
    }
    const last = transcript[transcript.length - 1];
    if (!last || last.speaker !== 'AI') {
      return;
    }
    if (!listening && micEnabled && speechSupported) {
      startListening();
    }
  }, [transcript, status, listening, micEnabled, speechSupported]);

  useEffect(() => {
    if (status !== 'active') {
      return;
    }
    clearAnswerTimer();
    setSecondsLeft(answerTimeSec);
    timerRef.current = window.setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          clearAnswerTimer();
          if (listening) {
            stopListening(true);
          } else {
            handleAction('respond', 'No response recorded.');
          }
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => {
      clearAnswerTimer();
    };
  }, [currentIndex, status]);

  useEffect(() => {
    const handleVisibility = () => {
      if (status !== 'active') {
        return;
      }
      if (document.hidden) {
        setFocusMessage('Focus lost: do not switch tabs during the interview.');
        setFocusWarnings((prev) => prev + 1);
      }
    };
    const handleBlur = () => {
      if (status !== 'active') {
        return;
      }
      setFocusMessage('Window lost focus: keep the interview tab active.');
      setFocusWarnings((prev) => prev + 1);
    };
    document.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('blur', handleBlur);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibility);
      window.removeEventListener('blur', handleBlur);
    };
  }, [status]);

  useEffect(() => {
    if (status !== 'active') {
      return;
    }
    if (focusWarnings >= maxWarnings && !autoEndedRef.current) {
      autoEndedRef.current = true;
      setFocusMessage('Interview ended due to focus violations.');
      handleAction('finish');
    }
  }, [focusWarnings, status]);

  useEffect(() => {
    if (!ttsEnabledRef.current) {
      return;
    }
    if (status !== 'active') {
      return;
    }
    const last = transcript[transcript.length - 1];
    if (!last || last.speaker !== 'AI') {
      return;
    }
    if (!('speechSynthesis' in window)) {
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(last.text);
    utterance.rate = 1;
    utterance.pitch = 1;
    window.speechSynthesis.speak(utterance);
  }, [transcript, status]);

  useEffect(() => {
    return () => {
      stopCamera();
      clearAnswerTimer();
      window.speechSynthesis?.cancel?.();
    };
  }, []);

  useEffect(() => {
    if (!streamRef.current) {
      return;
    }
    streamRef.current.getAudioTracks().forEach((track) => {
      track.enabled = micEnabled;
    });
  }, [micEnabled]);

  useEffect(() => {
    if (!micEnabled && listening) {
      stopListening(false);
    }
  }, [micEnabled, listening]);

  useEffect(() => {
    return () => {
      clearSilenceTimer();
    };
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />

      <div className="pl-[260px]">
        <main className="relative p-6">
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute -right-32 top-10 h-72 w-72 rounded-full bg-primary/10 blur-3xl" />
            <div className="absolute bottom-10 left-10 h-64 w-64 rounded-full bg-accent/10 blur-3xl" />
            <div className="absolute right-1/3 top-1/2 h-48 w-48 rounded-full bg-emerald-500/10 blur-3xl" />
          </div>

          <div className="relative space-y-6">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="relative overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-background via-background to-primary/5 p-8"
            >
              <div className="absolute left-10 top-0 h-24 w-24 rounded-full bg-primary/20 blur-2xl" />
              <div className="absolute bottom-0 right-6 h-28 w-28 rounded-full bg-accent/20 blur-2xl" />
              <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-primary">
                    <Sparkles className="h-3.5 w-3.5" />
                    AI Interview Lab
                  </div>
                  <h1 className="mt-4 text-3xl font-semibold tracking-tight md:text-4xl">
                    Run a crisp, signal-rich interview
                  </h1>
                  <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
                    Practice structured answers, track depth, and build confidence with feedback that
                    updates after every response.
                  </p>
                  {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <div
                    className={`flex items-center gap-2 rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] ${statusStyles[status]}`}
                  >
                    <span className="h-2 w-2 rounded-full bg-current" />
                    {statusLabel}
                  </div>
                  <div className="flex items-center gap-2 rounded-full border border-border/60 bg-card/60 px-3 py-1 text-xs">
                    <Camera className="h-3.5 w-3.5 text-primary" />
                    {cameraEnabled ? 'Camera live' : 'Camera off'}
                  </div>
                  <div className="rounded-2xl border border-border/60 bg-card/60 px-5 py-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      Session score
                    </p>
                    <p className="mt-1 text-2xl font-semibold text-foreground">
                      {Math.round(score)}
                    </p>
                  </div>
                </div>
              </div>
            </motion.div>

            <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <div className="space-y-6">
                {focusWarnings > 0 && (
                  <div className="rounded-2xl border border-amber-400/40 bg-amber-400/10 p-4 text-sm text-amber-500">
                    <div className="flex items-center gap-2 font-semibold">
                      <ShieldAlert className="h-4 w-4" />
                      Focus required ({Math.min(focusWarnings, maxWarnings)}/{maxWarnings})
                    </div>
                    <p className="mt-1 text-xs text-amber-200/90">{focusMessage}</p>
                  </div>
                )}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6 }}
                  className="rounded-3xl border border-border/60 bg-card/70 p-6 shadow-lg shadow-primary/5"
                >
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10">
                        <Target className="h-6 w-6 text-primary" />
                      </div>
                      <div>
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                          Current prompt
                        </p>
                        <h2 className="text-lg font-semibold">
                          {currentQuestion || 'Start a session to get your first question.'}
                        </h2>
                        {currentDifficulty && (
                          <p className="text-xs text-muted-foreground">
                            Difficulty: {currentDifficulty.toUpperCase()}
                          </p>
                        )}
                        {status === 'active' && (
                          <p className="text-xs text-muted-foreground">
                            Time left: {secondsLeft}s
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="destructive"
                        onClick={() => handleAction('finish')}
                        disabled={status !== 'active'}
                        className="rounded-full"
                      >
                        <Square className="mr-2 h-4 w-4" />
                        End session
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setTtsEnabled((prev) => !prev)}
                        className="rounded-full"
                      >
                        {ttsEnabled ? <Volume2 className="mr-2 h-4 w-4" /> : <VolumeX className="mr-2 h-4 w-4" />}
                        {ttsEnabled ? 'Voice on' : 'Voice off'}
                      </Button>
                      <Button
                        variant="outline"
                        onClick={() => setMicEnabled((prev) => !prev)}
                        className="rounded-full"
                      >
                        {micEnabled ? <Mic className="mr-2 h-4 w-4" /> : <MicOff className="mr-2 h-4 w-4" />}
                        {micEnabled ? 'Mic on' : 'Mic off'}
                      </Button>
                    </div>
                  </div>

                  <div className="mt-6 space-y-3">
                    <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      <span>Progress</span>
                      {totalQuestions ? (
                        <span>
                          Q{Math.min(currentIndex + 1, totalQuestions)}/{totalQuestions}
                        </span>
                      ) : (
                        <span>Waiting</span>
                      )}
                    </div>
                    <div className="h-2 w-full rounded-full bg-muted">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                        transition={{ duration: 0.9 }}
                        className="h-full rounded-full bg-gradient-to-r from-primary via-accent to-primary/70"
                      />
                    </div>
                    <p className="text-[11px] text-muted-foreground">
                      Focus lock active: switching tabs triggers warnings and may end the session.
                    </p>
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                  className="rounded-3xl border border-border/60 bg-gradient-to-br from-card/70 via-card/60 to-background p-6"
                >
                  <div className="mb-5 grid gap-4 md:grid-cols-[1.2fr_1fr]">
                    <div className="rounded-3xl border border-border/60 bg-muted/30 p-4">
                      <div className="flex items-center justify-between">
                        <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                          Candidate camera
                        </p>
                        <button
                          type="button"
                          onClick={cameraEnabled ? stopCamera : startCamera}
                          className="text-xs font-semibold text-primary"
                        >
                          {cameraEnabled ? 'Disable' : 'Enable'}
                        </button>
                      </div>
                      <div className="mt-3 overflow-hidden rounded-2xl border border-border/60 bg-background/80">
                        <video
                          ref={videoRef}
                          autoPlay
                          muted
                          playsInline
                          className="h-56 w-full object-cover"
                        />
                      </div>
                      {cameraError && <p className="mt-2 text-xs text-destructive">{cameraError}</p>}
                    </div>
                    <div className="rounded-3xl border border-border/60 bg-muted/20 p-4">
                      <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        AI interviewer
                      </p>
                      <div className="mt-3 flex h-56 flex-col items-center justify-center rounded-2xl border border-border/60 bg-gradient-to-br from-primary/15 via-background to-accent/10 text-center">
                        <Brain className="h-8 w-8 text-primary" />
                        <p className="mt-3 text-sm font-semibold text-foreground">SkillVerify AI</p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          Live interview mode
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <MessageSquare className="h-5 w-5 text-primary" />
                      <h3 className="text-lg font-semibold">Interview stream</h3>
                    </div>
                    <span className="text-xs uppercase tracking-[0.2em] text-muted-foreground">
                      {statusLabel}
                    </span>
                  </div>

                  <div className="mt-5 space-y-4">
                    {transcript.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border/70 bg-muted/30 p-6 text-center text-sm text-muted-foreground">
                        Your dialog will appear here once the session starts.
                      </div>
                    ) : (
                      transcript.map((item, index) => (
                        <div
                          key={index}
                          className={`flex gap-3 ${item.speaker === 'You' ? 'flex-row-reverse' : ''}`}
                        >
                          <div
                            className={`flex h-10 w-10 items-center justify-center rounded-2xl ${
                              item.speaker === 'AI'
                                ? 'bg-primary/15 text-primary'
                                : 'bg-accent/15 text-accent'
                            }`}
                          >
                            {item.speaker === 'AI' ? (
                              <Brain className="h-5 w-5" />
                            ) : (
                              <span className="text-xs font-semibold">SV</span>
                            )}
                          </div>
                          <div
                            className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                              item.speaker === 'AI'
                                ? 'bg-muted/60 text-foreground'
                                : 'bg-primary/10 text-foreground'
                            }`}
                          >
                            {item.text}
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  <div className="mt-6">
                    <div className="rounded-2xl border border-border/60 bg-background/80 p-4 text-sm">
                      <div className="flex items-center justify-between text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        <span>Live transcript</span>
                        <span>{listening ? 'Listening' : 'Idle'}</span>
                      </div>
                      <div className="mt-3 min-h-[90px] whitespace-pre-line text-sm text-foreground">
                        {liveTranscript ||
                          (status === 'active'
                            ? 'Press “Start speaking” and answer out loud.'
                            : 'Start a session to respond to questions.')}
                      </div>
                    </div>
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-muted-foreground">
                        Auto-sends after {silenceMs / 1000}s of silence. No buttons needed.
                      </p>
                      <div className="rounded-full border border-border/60 bg-muted/40 px-3 py-1 text-xs uppercase tracking-[0.2em] text-muted-foreground">
                        {listening ? 'Listening' : 'Waiting'}
                      </div>
                    </div>
                    {!speechSupported && (
                      <p className="mt-3 text-xs text-destructive">
                        Speech recognition is not supported in this browser. Use Chrome/Edge.
                      </p>
                    )}
                  </div>
                </motion.div>
              </div>

              <div className="space-y-6">
                <motion.div
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.2 }}
                  className="rounded-3xl border border-border/60 bg-card/70 p-6"
                >
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-5 w-5 text-accent" />
                    <h3 className="text-lg font-semibold">Signal dashboard</h3>
                  </div>
                  <div className="mt-4 space-y-4">
                    {metrics.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border/70 bg-muted/30 p-6 text-center text-sm text-muted-foreground">
                        Metrics appear as you answer.
                      </div>
                    ) : (
                      metrics.map((metric, index) => (
                        <div key={index}>
                          <div className="flex justify-between text-sm">
                            <span className="text-muted-foreground">{metric.label}</span>
                            <span className="font-semibold">{metric.value}%</span>
                          </div>
                          <div className="mt-2 h-2 rounded-full bg-muted">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${metric.value}%` }}
                              transition={{ duration: 0.9, delay: index * 0.1 }}
                              className={`h-full rounded-full ${
                                metric.color === 'primary'
                                  ? 'bg-gradient-to-r from-primary to-primary/60'
                                  : 'bg-gradient-to-r from-accent to-accent/60'
                              }`}
                            />
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.3 }}
                  className="rounded-3xl border border-border/60 bg-card/70 p-6"
                >
                  <h3 className="text-lg font-semibold">Coach notes</h3>
                  <div className="mt-4 space-y-3">
                    {feedback.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border/70 bg-muted/30 p-6 text-center text-sm text-muted-foreground">
                        Feedback shows after each answer.
                      </div>
                    ) : (
                      feedback.map((item, index) => (
                        <div
                          key={index}
                          className={`flex items-start gap-3 rounded-2xl p-3 ${
                            item.type === 'strength'
                              ? 'bg-emerald-500/10 text-emerald-500'
                              : 'bg-amber-500/10 text-amber-500'
                          }`}
                        >
                          {item.type === 'strength' ? (
                            <CheckCircle2 className="h-5 w-5 flex-shrink-0" />
                          ) : (
                            <AlertCircle className="h-5 w-5 flex-shrink-0" />
                          )}
                          <span className="text-sm text-foreground">{item.text}</span>
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, x: 30 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                  className="rounded-3xl border border-border/60 bg-card/70 p-6"
                >
                  <h3 className="text-lg font-semibold">Quick boosts</h3>
                  <div className="mt-4 space-y-3">
                    {tips.length === 0 ? (
                      <div className="rounded-2xl border border-dashed border-border/70 bg-muted/30 p-6 text-center text-sm text-muted-foreground">
                        Suggestions will appear when your pacing shifts.
                      </div>
                    ) : (
                      tips.map((tip, index) => (
                        <div
                          key={index}
                          className="rounded-2xl border border-border/60 bg-background/70 p-3 text-sm text-muted-foreground"
                        >
                          {tip}
                        </div>
                      ))
                    )}
                  </div>
                </motion.div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
