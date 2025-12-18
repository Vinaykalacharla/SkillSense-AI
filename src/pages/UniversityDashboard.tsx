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

const skillDistribution = [
  { name: 'React', students: 450 },
  { name: 'Python', students: 380 },
  { name: 'Java', students: 320 },
  { name: 'Node.js', students: 280 },
  { name: 'SQL', students: 420 },
  { name: 'AWS', students: 180 },
];

const placementTrend = [
  { month: 'Jan', placed: 45, target: 50 },
  { month: 'Feb', placed: 82, target: 100 },
  { month: 'Mar', placed: 125, target: 150 },
  { month: 'Apr', placed: 180, target: 200 },
  { month: 'May', placed: 230, target: 250 },
];

const readinessData = [
  { name: 'Placement Ready', value: 35, color: 'hsl(var(--primary))' },
  { name: 'Almost Ready', value: 40, color: 'hsl(var(--accent))' },
  { name: 'Needs Improvement', value: 25, color: 'hsl(var(--muted))' },
];

const interventions = [
  {
    batch: 'CSE 2025',
    issue: 'Low communication scores',
    affected: 45,
    suggestion: 'Conduct mock interview workshops',
    priority: 'high',
  },
  {
    batch: 'IT 2025',
    issue: 'Missing cloud skills',
    affected: 78,
    suggestion: 'AWS certification bootcamp',
    priority: 'medium',
  },
  {
    batch: 'ECE 2025',
    issue: 'Limited project experience',
    affected: 32,
    suggestion: 'Industry project partnerships',
    priority: 'high',
  },
];

export default function UniversityDashboard() {
  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="pt-24 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="container-custom">
          {/* Header */}
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
                IIT Delhi • Batch 2024-2025
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

          {/* Stats Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Total Students', value: '2,456', icon: Users, change: '+156' },
              { label: 'Avg. Skill Score', value: '78.5', icon: TrendingUp, change: '+5.2' },
              { label: 'Placement Ready', value: '68%', icon: Target, change: '+12%' },
              { label: 'Need Attention', value: '234', icon: AlertTriangle, change: '-45' },
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
                  <span
                    className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      stat.change.startsWith('+')
                        ? 'bg-green-500/10 text-green-400'
                        : 'bg-red-500/10 text-red-400'
                    }`}
                  >
                    {stat.change}
                  </span>
                </div>
                <div className="text-2xl font-bold">{stat.value}</div>
                <div className="text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>

          <div className="grid lg:grid-cols-3 gap-8 mb-8">
            {/* Skill Distribution Heatmap */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="lg:col-span-2 glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">Skill Distribution</h3>
              <div className="h-[300px]">
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
                    <Bar dataKey="students" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            {/* Placement Readiness */}
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1 }}
              className="glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">Placement Readiness</h3>
              <div className="h-[200px]">
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
              </div>
              <div className="space-y-2 mt-4">
                {readinessData.map((item, index) => (
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
                ))}
              </div>
            </motion.div>
          </div>

          {/* Placement Trend & Interventions */}
          <div className="grid lg:grid-cols-2 gap-8">
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
              className="glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">Placement Trend</h3>
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={placementTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="month"
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
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="placed"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      dot={{ fill: 'hsl(var(--primary))' }}
                    />
                    <Line
                      type="monotone"
                      dataKey="target"
                      stroke="hsl(var(--accent))"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3 }}
              className="glass-card p-6"
            >
              <h3 className="text-lg font-semibold mb-4">AI Intervention Suggestions</h3>
              <div className="space-y-4">
                {interventions.map((item, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-xl border-l-4 ${
                      item.priority === 'high'
                        ? 'border-l-red-500 bg-red-500/5'
                        : 'border-l-amber-500 bg-amber-500/5'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-medium">{item.batch}</span>
                      <span className="text-xs text-muted-foreground">
                        {item.affected} students
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground mb-2">{item.issue}</p>
                    <p className="text-sm font-medium text-primary">{item.suggestion}</p>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
