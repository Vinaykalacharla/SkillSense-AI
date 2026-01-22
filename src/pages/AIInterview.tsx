import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import {
  AlertCircle,
  Brain,
  CheckCircle2,
  MessageSquare,
  Play,
  Sparkles,
  Square,
  Target,
  TrendingUp,
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

const statusStyles = {
  idle: 'border-border/60 bg-muted/40 text-muted-foreground',
  active: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500',
  completed: 'border-primary/30 bg-primary/10 text-primary',
};

export default function AIInterview() {
  const [transcript, setTranscript] = useState<TranscriptItem[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [metrics, setMetrics] = useState<MetricItem[]>([]);
  const [tips, setTips] = useState<string[]>([]);
  const [status, setStatus] = useState<'idle' | 'active' | 'completed'>('idle');
  const [interviewState, setInterviewState] = useState<InterviewState>({});
  const [response, setResponse] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

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

  const handleAction = async (action: 'start' | 'respond' | 'finish') => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setError('Login required to start the interview.');
      return;
    }
    if (action === 'respond' && !response.trim()) {
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
          message: response.trim(),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data?.error || 'Interview action failed. Please try again.');
        return;
      }
      setError('');
      applyInterviewData(data);
      if (action === 'respond') {
        setResponse('');
      }
    } finally {
      setSending(false);
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
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="outline"
                        onClick={() => handleAction('start')}
                        disabled={status === 'active' || sending}
                        className="rounded-full"
                      >
                        <Play className="mr-2 h-4 w-4" />
                        {status === 'completed' ? 'Restart session' : 'Start session'}
                      </Button>
                      <Button
                        variant="destructive"
                        onClick={() => handleAction('finish')}
                        disabled={status !== 'active'}
                        className="rounded-full"
                      >
                        <Square className="mr-2 h-4 w-4" />
                        End session
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
                  </div>
                </motion.div>

                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                  className="rounded-3xl border border-border/60 bg-gradient-to-br from-card/70 via-card/60 to-background p-6"
                >
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
                    <textarea
                      className="w-full rounded-2xl border border-border/60 bg-background/80 p-4 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30"
                      placeholder={
                        status === 'active'
                          ? 'Craft a structured response...'
                          : 'Start a session to respond to questions.'
                      }
                      rows={4}
                      value={response}
                      onChange={(e) => setResponse(e.target.value)}
                      disabled={status !== 'active'}
                    />
                    <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                      <p className="text-xs text-muted-foreground">
                        Tip: Use STAR format and quantify impact.
                      </p>
                      <Button
                        variant="default"
                        onClick={() => handleAction('respond')}
                        disabled={status !== 'active' || sending || !response.trim()}
                        className="rounded-full"
                      >
                        Send response
                      </Button>
                    </div>
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
