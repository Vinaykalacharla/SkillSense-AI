import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import {
  Users,
  TrendingUp,
  Target,
  AlertTriangle,
  Download,
  Filter,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
  Legend,
} from 'recharts';

interface Summary {
  students: number;
  average_ready: number;
}

interface SkillDistribution {
  name: string;
  count: number;
}

export default function UniversityDashboard() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [skillDistribution, setSkillDistribution] = useState<SkillDistribution[]>([]);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch('http://127.0.0.1:8000/api/skills/university-dashboard/', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        setSummary(data?.summary || null);
        setSkillDistribution(Array.isArray(data?.skill_distribution) ? data.skill_distribution : []);
      })
      .catch(() => {
        setSummary(null);
        setSkillDistribution([]);
      });
  }, []);

  const readinessData = summary
    ? [
        { name: 'Placement Ready', value: Math.round(summary.average_ready || 0), color: 'hsl(var(--primary))' },
        { name: 'Almost Ready', value: Math.max(0, 100 - Math.round(summary.average_ready || 0)), color: 'hsl(var(--accent))' },
      ]
    : [];

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="pt-24 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="container-custom">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col md:flex-row md:items-center justify-between mb-8"
          >
            <div>
              <h1 className="text-3xl font-bold mb-2">
                University <span className="gradient-text">Analytics</span>
              </h1>
              <p className="text-muted-foreground">
                Batch performance and student readiness overview
              </p>
            </div>
            <div className="flex gap-3 mt-4 md:mt-0">
              <Button variant="outline">
                <Filter className="w-4 h-4 mr-2" />
                Filter
              </Button>
              <Button>
                <Download className="w-4 h-4 mr-2" />
                Export Report
              </Button>
            </div>
          </motion.div>

          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Total Students', value: summary?.students ?? '--', icon: Users, change: '--' },
              { label: 'Avg. Ready Score', value: summary?.average_ready ?? '--', icon: TrendingUp, change: '--' },
              { label: 'Placement Ready', value: summary ? `${summary.average_ready}%` : '--', icon: Target, change: '--' },
              { label: 'Need Attention', value: '--', icon: AlertTriangle, change: '--' },
            ].map((stat, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
                className="glass-card p-5"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <stat.icon className="w-5 h-5 text-primary" />
                  </div>
                  <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-muted/50 text-muted-foreground">
                    {stat.change}
                  </span>
                </div>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <div className="grid lg:grid-cols-3 gap-8 mb-8">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="lg:col-span-2 glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">Skill Distribution</h3>
              <div className="h-[300px]">
                {skillDistribution.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                    No skill distribution data yet
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={skillDistribution}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis
                        dataKey="name"
                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                      />
                      <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{
                          background: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                        }}
                      />
                      <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">Placement Readiness</h3>
              <div className="h-[200px]">
                {readinessData.length === 0 ? (
                  <div className="h-full flex items-center justify-center text-muted-foreground">
                    No readiness data yet
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={readinessData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        dataKey="value"
                      >
                        {readinessData.map((entry, index) => (
                          <Cell key={index} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
              <div className="space-y-2 mt-4">
                {readinessData.length === 0 ? (
                  <div className="text-center text-muted-foreground">No readiness data yet</div>
                ) : (
                  readinessData.map((item, index) => (
                    <div key={index} className="flex items-center justify-between text-sm">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-3 h-3 rounded-full"
                          style={{ background: item.color }}
                        />
                        {item.name}
                      </div>
                      <span className="font-medium">{item.value}%</span>
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          </div>

          <div className="grid lg:grid-cols-2 gap-8">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">Placement Trend</h3>
              <div className="h-[300px]">
                <div className="h-full flex items-center justify-center text-muted-foreground">
                  No placement trend data yet
                </div>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">AI Intervention Suggestions</h3>
              <div className="text-center text-muted-foreground py-6">
                No intervention data yet
              </div>
            </motion.div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
