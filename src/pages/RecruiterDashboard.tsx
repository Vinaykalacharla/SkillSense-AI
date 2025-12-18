import { useState } from 'react';
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

const candidates = [
  {
    id: 1,
    name: 'Rahul Sharma',
    title: 'Full Stack Developer',
    location: 'Delhi, India',
    university: 'IIT Delhi',
    experience: '2 years',
    score: 87,
    skills: ['React', 'Node.js', 'Python', 'AWS'],
    verified: true,
    authenticity: 95,
    image: 'https://i.pravatar.cc/100?img=3',
  },
  {
    id: 2,
    name: 'Priya Patel',
    title: 'Data Scientist',
    location: 'Bangalore, India',
    university: 'IISc Bangalore',
    experience: '1 year',
    score: 92,
    skills: ['Python', 'TensorFlow', 'SQL', 'Tableau'],
    verified: true,
    authenticity: 98,
    image: 'https://i.pravatar.cc/100?img=1',
  },
  {
    id: 3,
    name: 'Amit Kumar',
    title: 'Backend Engineer',
    location: 'Mumbai, India',
    university: 'NIT Trichy',
    experience: '3 years',
    score: 85,
    skills: ['Java', 'Spring Boot', 'PostgreSQL', 'Docker'],
    verified: true,
    authenticity: 92,
    image: 'https://i.pravatar.cc/100?img=4',
  },
];

const filters = [
  { label: 'Skills', options: ['React', 'Python', 'Node.js', 'Java', 'AWS'] },
  { label: 'Experience', options: ['0-1 years', '1-3 years', '3-5 years', '5+ years'] },
  { label: 'Location', options: ['Delhi', 'Bangalore', 'Mumbai', 'Remote'] },
  { label: 'Score', options: ['90+', '80+', '70+', 'All'] },
];

export default function RecruiterDashboard() {
  const [selectedCandidate, setSelectedCandidate] = useState(candidates[0]);
  const [compareMode, setCompareMode] = useState(false);

  const radarData = [
    { skill: 'React', level: 85 },
    { skill: 'Node.js', level: 80 },
    { skill: 'Python', level: 75 },
    { skill: 'SQL', level: 70 },
    { skill: 'AWS', level: 60 },
    { skill: 'Git', level: 90 },
  ];

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
            className="mb-8"
          >
            <h1 className="text-3xl font-bold mb-2">
              Find <span className="gradient-text">Verified Talent</span>
            </h1>
            <p className="text-muted-foreground">
              Browse pre-verified candidates with authentic skills
            </p>
          </motion.div>

          {/* Search & Filters */}
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
                  placeholder="Search by skills, name, or university..."
                  className="input-field pl-12 w-full"
                />
              </div>
              <div className="flex gap-3 flex-wrap">
                {filters.map((filter) => (
                  <button
                    key={filter.label}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl bg-muted/50 hover:bg-muted text-sm transition-colors"
                  >
                    {filter.label}
                    <ChevronDown className="w-4 h-4" />
                  </button>
                ))}
                <Button variant="outline">
                  <Filter className="w-4 h-4 mr-2" />
                  More Filters
                </Button>
              </div>
            </div>
          </motion.div>

          <div className="grid lg:grid-cols-3 gap-8">
            {/* Candidates List */}
            <div className="lg:col-span-2 space-y-4">
              <div className="flex items-center justify-between mb-4">
                <span className="text-sm text-muted-foreground">
                  Showing {candidates.length} verified candidates
                </span>
                <Button
                  variant={compareMode ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setCompareMode(!compareMode)}
                >
                  Compare Mode
                </Button>
              </div>

              {candidates.map((candidate, index) => (
                <motion.div
                  key={candidate.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.5, delay: index * 0.1 }}
                  onClick={() => setSelectedCandidate(candidate)}
                  className={`glass-card p-6 cursor-pointer card-hover ${
                    selectedCandidate.id === candidate.id
                      ? 'border-primary/50 glow-primary'
                      : ''
                  }`}
                >
                  <div className="flex items-start gap-4">
                    {compareMode && (
                      <input type="checkbox" className="mt-2 w-5 h-5 rounded" />
                    )}
                    <img
                      src={candidate.image}
                      alt={candidate.name}
                      className="w-16 h-16 rounded-xl object-cover"
                    />
                    <div className="flex-1">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold text-lg">{candidate.name}</h3>
                            {candidate.verified && (
                              <BadgeCheck className="w-5 h-5 text-primary" />
                            )}
                          </div>
                          <p className="text-muted-foreground">{candidate.title}</p>
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
                          {candidate.location}
                        </span>
                        <span className="flex items-center gap-1">
                          <GraduationCap className="w-4 h-4" />
                          {candidate.university}
                        </span>
                        <span className="flex items-center gap-1">
                          <Briefcase className="w-4 h-4" />
                          {candidate.experience}
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-2 mt-3">
                        {candidate.skills.map((skill) => (
                          <span
                            key={skill}
                            className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>

                      {/* Authenticity */}
                      <div className="flex items-center gap-2 mt-4">
                        <span className="text-xs text-muted-foreground">
                          Authenticity:
                        </span>
                        <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden max-w-[200px]">
                          <div
                            className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded-full"
                            style={{ width: `${candidate.authenticity}%` }}
                          />
                        </div>
                        <span className="text-xs font-medium text-green-400">
                          {candidate.authenticity}%
                        </span>
                      </div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Selected Candidate Detail */}
            <div className="space-y-6">
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6 }}
                className="glass-card p-6 sticky top-24"
              >
                <div className="text-center mb-6">
                  <img
                    src={selectedCandidate.image}
                    alt={selectedCandidate.name}
                    className="w-20 h-20 rounded-2xl mx-auto mb-4 object-cover"
                  />
                  <h3 className="text-xl font-semibold">{selectedCandidate.name}</h3>
                  <p className="text-muted-foreground">{selectedCandidate.title}</p>
                </div>

                {/* Skill Radar */}
                <div className="h-[200px] mb-6">
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
                </div>

                {/* Actions */}
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
              </motion.div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  );
}
