import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import {
  Search,
  Filter,
  BadgeCheck,
  Star,
  MapPin,
  Briefcase,
  GraduationCap,
  ChevronDown,
  Eye,
  MessageSquare,
  Download,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts';

interface Candidate {
  id: number;
  name: string;
  college: string;
  role: string;
  location: string;
  score: number;
  skills: { name: string; score: number }[];
}

export default function RecruiterDashboard() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [selectedCandidate, setSelectedCandidate] = useState<Candidate | null>(null);
  const [compareMode, setCompareMode] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch('http://127.0.0.1:8000/api/skills/recruiter-dashboard/', {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((res) => res.json())
      .then((data) => {
        const list = Array.isArray(data?.candidates) ? data.candidates : [];
        setCandidates(list);
        setSelectedCandidate(list[0] || null);
      })
      .catch(() => {
        setCandidates([]);
        setSelectedCandidate(null);
      });
  }, []);

  const radarData = (selectedCandidate?.skills || []).map((skill) => ({
    skill: skill.name,
    level: skill.score ?? 50,
  }));

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="pt-24 pb-16 px-4 sm:px-6 lg:px-8">
        <div className="container-custom">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <h1 className="text-3xl font-bold mb-2">
              Find <span className="gradient-text">Verified Talent</span>
            </h1>
            <p className="text-muted-foreground">
              Browse verified candidates with authentic skills
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6 mb-8"
          >
            <div className="flex flex-col lg:flex-row gap-4">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
                <input
                  type="text"
                  placeholder="Search by skills, name, or college..."
                  className="input-field pl-12 w-full"
                />
              </div>
              <div className="flex gap-3 flex-wrap">
                <Button variant="outline">
                  <Filter className="w-4 h-4 mr-2" />
                  Filters
                </Button>
                <Button variant={compareMode ? 'default' : 'outline'} onClick={() => setCompareMode(!compareMode)}>
                  Compare Mode
                </Button>
              </div>
            </div>
          </motion.div>

          <div className="grid lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-muted-foreground">
                  Showing {candidates.length} verified candidates
                </span>
              </div>

              {candidates.length === 0 ? (
                <div className="glass-card p-6 text-center text-muted-foreground">
                  No verified candidates yet
                </div>
              ) : (
                candidates.map((candidate, index) => (
                  <motion.div
                    key={candidate.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    onClick={() => setSelectedCandidate(candidate)}
                    className={`glass-card p-6 cursor-pointer card-hover ${
                      selectedCandidate?.id === candidate.id
                        ? 'border-primary/50 glow-primary'
                        : ''
                    }`}
                  >
                    <div className="flex items-start gap-4">
                      {compareMode && (
                        <input type="checkbox" className="mt-2 w-5 h-5 rounded" />
                      )}
                      <div className="w-16 h-16 rounded-xl bg-primary/10 flex items-center justify-center">
                        <span className="text-lg font-semibold text-primary">
                          {candidate.name.slice(0, 1)}
                        </span>
                      </div>
                      <div className="flex-1">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-2">
                              <h3 className="font-semibold text-lg">{candidate.name}</h3>
                              <BadgeCheck className="w-5 h-5 text-primary" />
                            </div>
                            <p className="text-muted-foreground">{candidate.role}</p>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-bold gradient-text">
                              {candidate.score}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Overall Score
                            </div>
                          </div>
                        </div>

                        <div className="flex flex-wrap gap-4 mt-3 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <MapPin className="w-4 h-4" />
                            {candidate.location || 'Location N/A'}
                          </span>
                          <span className="flex items-center gap-1">
                            <GraduationCap className="w-4 h-4" />
                            {candidate.college || 'College N/A'}
                          </span>
                          <span className="flex items-center gap-1">
                            <Briefcase className="w-4 h-4" />
                            {candidate.role || 'Role N/A'}
                          </span>
                        </div>

                        <div className="flex flex-wrap gap-2 mt-3">
                          {candidate.skills.length === 0 ? (
                            <span className="text-xs text-muted-foreground">No skills listed</span>
                          ) : (
                            candidate.skills.map((skill) => (
                              <span
                                key={skill.name}
                                className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium"
                              >
                                {skill.name}
                              </span>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                ))
              )}
            </div>

            <div className="space-y-6">
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6 }}
                className="glass-card p-6 sticky top-24"
              >
                {selectedCandidate ? (
                  <>
                    <div className="text-center mb-6">
                      <div className="w-20 h-20 rounded-2xl mx-auto mb-4 bg-primary/10 flex items-center justify-center">
                        <span className="text-xl font-semibold text-primary">
                          {selectedCandidate.name.slice(0, 1)}
                        </span>
                      </div>
                      <h3 className="text-xl font-semibold">{selectedCandidate.name}</h3>
                      <p className="text-muted-foreground">{selectedCandidate.role}</p>
                    </div>

                    <div className="h-[200px] mb-6">
                      {radarData.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-muted-foreground">
                          No skill scores yet
                        </div>
                      ) : (
                        <ResponsiveContainer width="100%" height="100%">
                          <RadarChart data={radarData}>
                            <PolarGrid stroke="hsl(var(--border))" />
                            <PolarAngleAxis
                              dataKey="skill"
                              tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }}
                            />
                            <Radar
                              dataKey="level"
                              stroke="hsl(var(--primary))"
                              fill="hsl(var(--primary))"
                              fillOpacity={0.3}
                            />
                          </RadarChart>
                        </ResponsiveContainer>
                      )}
                    </div>

                    <div className="space-y-3">
                      <Button className="w-full">
                        <Eye className="w-4 h-4 mr-2" />
                        View Full Profile
                      </Button>
                      <Button variant="outline" className="w-full">
                        <MessageSquare className="w-4 h-4 mr-2" />
                        Contact
                      </Button>
                      <Button variant="ghost" className="w-full">
                        <Download className="w-4 h-4 mr-2" />
                        Download Resume
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="text-center text-muted-foreground py-6">
                    Select a candidate to view details
                  </div>
                )}
              </motion.div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
