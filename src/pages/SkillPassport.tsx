import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import {
  BadgeCheck,
  Download,
  Share2,
  QrCode,
  Shield,
  Star,
  ExternalLink,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
} from 'recharts';
import { useState } from 'react';

const skillData = [
  { skill: 'React', level: 85 },
  { skill: 'Python', level: 75 },
  { skill: 'SQL', level: 70 },
  { skill: 'Node.js', level: 80 },
  { skill: 'Git', level: 90 },
  { skill: 'AWS', level: 60 },
];

const barData = [
  { name: 'Coding', score: 87 },
  { name: 'Communication', score: 72 },
  { name: 'Problem Solving', score: 85 },
  { name: 'Teamwork', score: 78 },
];

const verifiedSkills = [
  { name: 'React.js', level: 'Expert', evidence: 3, verified: true },
  { name: 'TypeScript', level: 'Intermediate', evidence: 2, verified: true },
  { name: 'Node.js', level: 'Intermediate', evidence: 4, verified: true },
  { name: 'Python', level: 'Intermediate', evidence: 2, verified: true },
  { name: 'SQL', level: 'Intermediate', evidence: 3, verified: true },
  { name: 'Git', level: 'Expert', evidence: 5, verified: true },
];

export default function SkillPassport() {
  const [expandedSkill, setExpandedSkill] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />

      <div className="pl-[260px]">
        <main className="p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-bold mb-2">Verified Skill Passport</h1>
                <p className="text-muted-foreground">
                  Your authenticated digital credential
                </p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline">
                  <Share2 className="w-4 h-4 mr-2" />
                  Share
                </Button>
                <Button variant="default">
                  <Download className="w-4 h-4 mr-2" />
                  Download PDF
                </Button>
              </div>
            </div>
          </motion.div>

          {/* Passport Card */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="glass-card p-8 mb-8 relative overflow-hidden"
          >
            {/* Decorative Elements */}
            <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-bl from-primary/10 to-transparent rounded-full blur-3xl" />
            <div className="absolute bottom-0 left-0 w-48 h-48 bg-gradient-to-tr from-accent/10 to-transparent rounded-full blur-3xl" />

            {/* Header */}
            <div className="relative flex items-start justify-between mb-8">
              <div className="flex items-center gap-4">
                <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center">
                  <span className="text-3xl font-bold text-primary-foreground">RS</span>
                </div>
                <div>
                  <h2 className="text-2xl font-bold">Rahul Sharma</h2>
                  <p className="text-muted-foreground">Computer Science • IIT Delhi</p>
                  <div className="flex items-center gap-2 mt-2">
                    <BadgeCheck className="w-5 h-5 text-primary" />
                    <span className="text-sm text-primary font-medium">Verified Profile</span>
                  </div>
                </div>
              </div>

              {/* QR Code Placeholder */}
              <div className="text-center">
                <div className="w-24 h-24 rounded-xl bg-white/10 border border-border/50 flex items-center justify-center mb-2">
                  <QrCode className="w-16 h-16 text-muted-foreground" />
                </div>
                <span className="text-xs text-muted-foreground">Scan to verify</span>
              </div>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4 mb-8">
              {[
                { label: 'Overall Score', value: '87/100', icon: Star },
                { label: 'Skills Verified', value: '12', icon: BadgeCheck },
                { label: 'Evidence Items', value: '24', icon: Shield },
                { label: 'Authenticity', value: '95%', icon: Shield },
              ].map((stat, index) => (
                <div key={index} className="text-center p-4 rounded-xl bg-muted/30">
                  <stat.icon className="w-6 h-6 mx-auto mb-2 text-primary" />
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <div className="text-xs text-muted-foreground">{stat.label}</div>
                </div>
              ))}
            </div>

            {/* Charts */}
            <div className="grid md:grid-cols-2 gap-8">
              <div>
                <h3 className="font-semibold mb-4">Skill Radar</h3>
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={skillData}>
                      <PolarGrid stroke="hsl(var(--border))" />
                      <PolarAngleAxis
                        dataKey="skill"
                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                      />
                      <Radar
                        dataKey="level"
                        stroke="hsl(var(--primary))"
                        fill="hsl(var(--primary))"
                        fillOpacity={0.3}
                        strokeWidth={2}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div>
                <h3 className="font-semibold mb-4">Core Competencies</h3>
                <div className="h-[250px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={barData} layout="vertical">
                      <XAxis type="number" domain={[0, 100]} hide />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                        width={100}
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'hsl(var(--card))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                        }}
                      />
                      <Bar
                        dataKey="score"
                        fill="hsl(var(--accent))"
                        radius={[0, 4, 4, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Verified Skills List */}
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            className="glass-card p-6"
          >
            <h3 className="text-lg font-semibold mb-6">Verified Skills & Evidence</h3>
            <div className="space-y-3">
              {verifiedSkills.map((skill, index) => (
                <div key={index} className="border border-border/50 rounded-xl overflow-hidden">
                  <button
                    onClick={() =>
                      setExpandedSkill(expandedSkill === skill.name ? null : skill.name)
                    }
                    className="w-full p-4 flex items-center justify-between hover:bg-muted/30 transition-colors"
                  >
                    <div className="flex items-center gap-4">
                      <BadgeCheck className="w-5 h-5 text-primary" />
                      <div className="text-left">
                        <div className="font-medium">{skill.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {skill.level} • {skill.evidence} evidence items
                        </div>
                      </div>
                    </div>
                    <ChevronDown
                      className={`w-5 h-5 text-muted-foreground transition-transform ${
                        expandedSkill === skill.name ? 'rotate-180' : ''
                      }`}
                    />
                  </button>

                  {expandedSkill === skill.name && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="px-4 pb-4 border-t border-border/50"
                    >
                      <div className="pt-4 space-y-3">
                        {[
                          { type: 'Code', source: 'GitHub Repository', date: 'Jan 18, 2025' },
                          { type: 'Project', source: 'Portfolio Website', date: 'Jan 15, 2025' },
                          { type: 'Assessment', source: 'Technical Quiz', date: 'Jan 12, 2025' },
                        ].map((evidence, i) => (
                          <div
                            key={i}
                            className="flex items-center justify-between p-3 rounded-lg bg-muted/30"
                          >
                            <div>
                              <div className="text-sm font-medium">{evidence.source}</div>
                              <div className="text-xs text-muted-foreground">
                                {evidence.type} • {evidence.date}
                              </div>
                            </div>
                            <Button variant="ghost" size="sm">
                              <ExternalLink className="w-4 h-4" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </motion.div>
                  )}
                </div>
              ))}
            </div>
          </motion.div>
        </main>
      </div>
    </div>
  );
}
