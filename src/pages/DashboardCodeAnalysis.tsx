import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { Code, LineChart } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { buildApiUrl } from '@/lib/api';

interface AnalysisItem {
  id: number;
  repo_name?: string;
  repo_url: string;
  description: string;
  score: number;
  metrics: Record<string, any>;
  status: string;
  created_at: string;
}

export default function DashboardCodeAnalysis() {
  const [items, setItems] = useState<AnalysisItem[]>([]);
  const [repoUrl, setRepoUrl] = useState('');
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch(buildApiUrl('/api/skills/code-analysis/'), {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setItems(Array.isArray(data?.items) ? data.items : []))
      .catch(() => setItems([]));
  }, []);

  const handleAnalyze = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !repoUrl.trim()) {
      setMessage('Enter a valid GitHub repository URL.');
      return;
    }
    setMessage('');
    setRunning(true);
    try {
      const res = await fetch(buildApiUrl('/api/skills/code-analysis/'), {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ repo_url: repoUrl.trim() }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok) {
        setItems((prev) => [data, ...prev]);
        setRepoUrl('');
        setMessage('Analysis completed.');
      } else {
        setMessage(data?.error || 'Unable to run analysis right now.');
      }
    } catch {
      setMessage('Network error. Please try again.');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />
      <div className="pl-[260px]">
        <main className="p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <h1 className="text-2xl font-bold mb-2">Code Analysis</h1>
            <p className="text-muted-foreground">Repository insights and quality checks</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6"
          >
            <div className="flex flex-col md:flex-row gap-4 mb-6">
              <Input
                placeholder="Repository URL"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
              />
              <Button onClick={handleAnalyze} disabled={running || !repoUrl.trim()}>
                <LineChart className="w-4 h-4 mr-2" />
                {running ? 'Analyzing...' : 'Run Analysis'}
              </Button>
            </div>
            {message ? (
              <div className="mb-4 rounded-lg border border-border/50 bg-muted/40 px-3 py-2 text-sm text-muted-foreground">
                {message}
              </div>
            ) : null}

            {items.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Code className="w-10 h-10 mb-3 text-primary" />
                No code analysis yet
              </div>
            ) : (
              <div className="space-y-3">
                {items.map((item) => (
                  <div key={item.id} className="p-4 rounded-xl bg-muted/30">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{item.repo_name || item.repo_url}</div>
                        <div className="text-xs text-muted-foreground">{item.description}</div>
                      </div>
                      <div className="text-lg font-semibold">{item.score}</div>
                    </div>
                    <div className="grid md:grid-cols-3 gap-3 mt-4 text-sm">
                      {Object.entries(item.metrics || {}).map(([key, value]) => {
                        const displayValue = Array.isArray(value)
                          ? value.join(', ')
                          : typeof value === 'boolean'
                          ? value ? 'Yes' : 'No'
                          : value;
                        return (
                          <div key={key} className="p-3 rounded-lg bg-background/50 border border-border/50">
                            <div className="text-muted-foreground text-xs">{key}</div>
                            <div className="font-medium">{String(displayValue)}</div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
