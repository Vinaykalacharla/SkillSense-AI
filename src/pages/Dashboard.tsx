import { motion } from 'framer-motion';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { ScoreCards } from '@/components/dashboard/ScoreCards';
import { SkillRadar } from '@/components/dashboard/SkillRadar';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { RecommendedActions } from '@/components/dashboard/RecommendedActions';
import { VerificationTimeline } from '@/components/dashboard/VerificationTimeline';
import { PerformanceTrends } from '@/components/dashboard/PerformanceTrends';
import { Bell, Search, User, RefreshCcw, ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { buildApiUrl } from '@/lib/api';

export default function Dashboard() {
  const navigate = useNavigate();
  const [userName, setUserName] = useState('Student');
  const [scores, setScores] = useState<Record<string, number> | null>(null);
  const [breakdown, setBreakdown] = useState<Record<string, Record<string, number>> | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [profileVerified, setProfileVerified] = useState(false);
  const [githubInsights, setGithubInsights] = useState<{
    top_languages: Array<[string, number]>;
    forked: number;
    original: number;
    fork_ratio: number;
  } | null>(null);

  useEffect(() => {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      try {
        const parsed = JSON.parse(storedUser);
        setUserName(parsed.full_name || parsed.username || 'Student');
      } catch (e) {
        setUserName('Student');
      }
    }

    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }

    fetch(buildApiUrl('/api/accounts/dashboard/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data?.user?.full_name || data?.user?.username) {
          setUserName(data.user.full_name || data.user.username);
        }
        if (typeof data?.user?.profile_verified === 'boolean') {
          setProfileVerified(data.user.profile_verified);
        }
        if (data?.scores) {
          setScores(data.scores);
        }
        if (data?.breakdown) {
          setBreakdown(data.breakdown);
        }
        if (data?.github_insights) {
          setGithubInsights(data.github_insights);
        }
      })
      .catch(() => {
        // Keep fallback data on network error.
      });
  }, []);

  const handleRecalculate = () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    setRefreshing(true);
    fetch(buildApiUrl('/api/accounts/recalculate/'), {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        if (data?.scores) {
          setScores(data.scores);
        }
        if (data?.breakdown) {
          setBreakdown(data.breakdown);
        }
        if (data?.github_insights) {
          setGithubInsights(data.github_insights);
        }
      })
      .finally(() => setRefreshing(false));
  };

  const handleDownloadReport = () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    setDownloading(true);
    fetch(buildApiUrl('/api/accounts/score-report/'), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => {
        if (!res.ok) {
          throw new Error('Failed to download report');
        }
        return res.blob();
      })
      .then((blob) => {
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = 'skillverify-score-report.pdf';
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
      })
      .finally(() => setDownloading(false));
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />
      
      {/* Main Content */}
      <div className="pl-[260px]">
        {/* Top Bar */}
        <header className="h-16 border-b border-border/50 flex items-center justify-between px-6 sticky top-0 bg-background/80 backdrop-blur-xl z-30">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold">Dashboard</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search..."
                className="input-field pl-10 w-64"
              />
            </div>
            <Button
              variant="outline"
              className="hidden md:flex"
              onClick={handleRecalculate}
              disabled={refreshing}
            >
              <RefreshCcw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              {refreshing ? 'Recalculating' : 'Recalculate Scores'}
            </Button>
            <Button
              variant="outline"
              className="hidden md:flex"
              onClick={handleDownloadReport}
              disabled={downloading}
            >
              {downloading ? 'Downloading...' : 'Export PDF'}
            </Button>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full" />
            </Button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <User className="w-5 h-5 text-primary-foreground" />
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="p-6">
          {/* Welcome */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <h2 className="text-2xl font-bold mb-2">
              Welcome back, <span className="gradient-text">{userName}</span>
            </h2>
            <p className="text-muted-foreground">
              Your skill verification is 75% complete. Keep going!
            </p>
          </motion.div>

          {/* Score Cards */}
          <div className="mb-8">
            <ScoreCards scores={scores ?? undefined} />
          </div>

          {breakdown && (
            <div className="mb-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-lg font-semibold">Score Breakdown</h3>
                  <p className="text-xs text-muted-foreground">Signal-level breakdown with weight highlights</p>
                </div>
                <div className="text-xs text-muted-foreground">Precision view</div>
              </div>
              <div className="grid md:grid-cols-2 gap-4 items-start">
                {Object.entries(breakdown)
                  .sort(([keyA], [keyB]) => {
                    const order = [
                      'coding_skill_index',
                      'communication_score',
                      'authenticity_score',
                      'placement_ready',
                    ];
                    return order.indexOf(keyA) - order.indexOf(keyB);
                  })
                  .map(([key, parts]) => {
                    const items = Object.entries(parts);
                    const total = items.reduce((acc, [, value]) => acc + (Number(value) || 0), 0);
                    const palette =
                      key === 'coding_skill_index'
                        ? 'from-blue-500/20 to-cyan-400/10'
                      : key === 'communication_score'
                      ? 'from-emerald-500/20 to-lime-400/10'
                      : key === 'authenticity_score'
                      ? 'from-amber-500/20 to-orange-400/10'
                      : 'from-sky-500/20 to-indigo-400/10';

                    return (
                      <Tooltip key={key}>
                        <TooltipTrigger asChild>
                          <div
                            className={`rounded-2xl border border-border/60 p-5 bg-gradient-to-br ${palette} cursor-pointer transition-shadow hover:shadow-lg hover:shadow-primary/10`}
                          >
                            <div className="flex items-center justify-between mb-3">
                              <div className="text-sm font-semibold">{key.replace('_', ' ')}</div>
                              <div className="text-xs text-muted-foreground">
                                Total {Math.round(total)}
                              </div>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Tap to see breakdown
                            </div>
                          </div>
                        </TooltipTrigger>
                        <TooltipContent
                          side="bottom"
                          align="start"
                          className="w-[320px] max-h-[60vh] overflow-y-auto rounded-2xl border border-border/60 bg-background/95 p-4 shadow-xl"
                        >
                          <div className="flex items-center justify-between mb-3">
                            <div className="text-sm font-semibold">{key.replace('_', ' ')}</div>
                            <div className="text-xs text-muted-foreground">
                              Total {Math.round(total)}
                            </div>
                          </div>
                          <div className="space-y-2">
                            {items.map(([label, value]) => {
                              const numeric = Number(value) || 0;
                              const width = total > 0 ? Math.min(100, (numeric / total) * 100) : 0;
                              return (
                                <div
                                  key={label}
                                  className="rounded-xl border border-border/50 bg-muted/40 p-3"
                                >
                                  <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                                    <span>{label.replace('_', ' ')}</span>
                                    <span className="text-foreground font-medium">
                                      {Math.round(numeric)}
                                    </span>
                                  </div>
                                  <div className="h-2 rounded-full bg-muted/60 overflow-hidden">
                                    <div
                                      className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                                      style={{ width: `${width}%` }}
                                    />
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    );
                  })}
              </div>
            </div>
          )}

          {githubInsights && (
            <div className="mb-8 glass-card p-6">
              <h3 className="text-lg font-semibold mb-4">GitHub Repo Insights</h3>
              <div className="grid md:grid-cols-2 gap-4">
                <div className="rounded-xl border border-border/50 p-4">
                  <div className="text-sm font-semibold mb-3">Languages Used</div>
                  <div className="flex flex-wrap gap-2">
                    {githubInsights.top_languages?.length ? (
                      githubInsights.top_languages.map(([lang, count]) => (
                        <span
                          key={lang}
                          className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs"
                        >
                          {lang} ({count})
                        </span>
                      ))
                    ) : (
                      <span className="text-sm text-muted-foreground">No language data</span>
                    )}
                  </div>
                </div>
                <div className="rounded-xl border border-border/50 p-4">
                  <div className="text-sm font-semibold mb-3">Repo Ownership</div>
                  <div className="space-y-2 text-sm text-muted-foreground">
                    <div className="flex items-center justify-between">
                      <span>Original repos</span>
                      <span className="text-foreground">{githubInsights.original ?? 0}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Forked repos</span>
                      <span className="text-foreground">{githubInsights.forked ?? 0}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Fork ratio</span>
                      <span className="text-foreground">
                        {Math.round((githubInsights.fork_ratio ?? 0) * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Main Grid */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Left Column */}
            <div className="lg:col-span-2 space-y-6">
              <PerformanceTrends />
              <SkillRadar />
              <RecentActivity />
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              <div className="glass-card p-6">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="w-5 h-5 text-primary" />
                    <h3 className="font-semibold">Skill Verification</h3>
                  </div>
                  <span
                    className={`text-xs font-semibold px-2 py-1 rounded-full ${
                      profileVerified
                        ? 'bg-primary/15 text-primary'
                        : 'bg-muted/40 text-muted-foreground'
                    }`}
                  >
                    {profileVerified ? 'Verified' : 'Pending'}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground mb-4">
                  {profileVerified
                    ? 'Your profile is verified after completing the AI interview.'
                    : 'Complete the AI interview to verify your profile.'}
                </p>
                {!profileVerified && (
                  <Button variant="outline" onClick={() => navigate('/dashboard/interview')}>
                    Start AI Interview
                  </Button>
                )}
              </div>
              <RecommendedActions />
              <VerificationTimeline />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}



