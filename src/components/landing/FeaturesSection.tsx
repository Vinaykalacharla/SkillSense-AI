import { motion } from 'framer-motion';
import { 
  Layers, 
  ShieldCheck, 
  Mic, 
  FileCheck, 
  Target, 
  Sparkles,
  Code,
  Video,
  FileText,
  TrendingUp
} from 'lucide-react';

const features = [
  {
    icon: Layers,
    title: 'Multimodal Skill Extraction',
    description: 'AI analyzes code, documents, videos, and interviews to build a complete skill profile.',
    gradient: 'from-primary to-primary/50',
  },
  {
    icon: ShieldCheck,
    title: 'Fraud Detection',
    description: 'Advanced algorithms detect copied code, plagiarized content, and inauthentic claims.',
    gradient: 'from-accent to-accent/50',
  },
  {
    icon: Mic,
    title: 'AI Interview Simulator',
    description: 'Practice with AI interviewers that evaluate communication, confidence, and technical depth.',
    gradient: 'from-primary to-accent',
  },
  {
    icon: FileCheck,
    title: 'Verified Skill Passport',
    description: 'Digital credentials with QR verification and evidence-backed skill attestations.',
    gradient: 'from-accent to-primary',
  },
  {
    icon: Target,
    title: 'Placement Readiness Score',
    description: 'AI calculates your job-readiness based on verified skills and industry requirements.',
    gradient: 'from-primary to-primary/50',
  },
  {
    icon: Sparkles,
    title: 'AI Mentor Twin',
    description: 'Personalized 90-day improvement roadmap based on your skill gaps and career goals.',
    gradient: 'from-accent to-accent/50',
  },
];

const dataTypes = [
  { icon: Code, label: 'Code Analysis', color: 'text-primary' },
  { icon: FileText, label: 'Document Parsing', color: 'text-accent' },
  { icon: Video, label: 'Video Analysis', color: 'text-primary' },
  { icon: TrendingUp, label: 'Performance Tracking', color: 'text-accent' },
];

export function FeaturesSection() {
  return (
    <section id="features" className="section-padding relative">
      <div className="container-custom">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-medium text-accent uppercase tracking-wider">Features</span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mt-4 mb-6">
            Everything You Need for <span className="gradient-text">Skill Verification</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Comprehensive tools powered by cutting-edge AI to discover, verify, and showcase authentic talent.
          </p>
        </motion.div>

        {/* Data Types Bar */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="flex flex-wrap justify-center gap-4 mb-16"
        >
          {dataTypes.map((type, index) => (
            <div key={index} className="glass px-4 py-2 rounded-full flex items-center gap-2">
              <type.icon className={`w-4 h-4 ${type.color}`} />
              <span className="text-sm font-medium">{type.label}</span>
            </div>
          ))}
        </motion.div>

        {/* Features Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="group"
            >
              <div className="glass-card p-6 h-full card-hover relative overflow-hidden">
                {/* Gradient Glow on Hover */}
                <div className={`absolute inset-0 bg-gradient-to-br ${feature.gradient} opacity-0 group-hover:opacity-5 transition-opacity duration-500`} />
                
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center mb-4`}>
                  <feature.icon className="w-6 h-6 text-primary-foreground" />
                </div>

                <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
                <p className="text-muted-foreground text-sm">{feature.description}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
