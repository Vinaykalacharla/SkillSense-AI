import { motion } from 'framer-motion';
import { Upload, Brain, BadgeCheck, ArrowRight } from 'lucide-react';

const steps = [
  {
    icon: Upload,
    title: 'Upload Your Work',
    description: 'Submit code from GitHub, documents, project videos, or take AI interviews.',
    color: 'primary',
  },
  {
    icon: Brain,
    title: 'Multimodal AI Analysis',
    description: 'Our AI analyzes patterns, detects authenticity, and extracts real skills.',
    color: 'accent',
  },
  {
    icon: BadgeCheck,
    title: 'Verified Skill Passport',
    description: 'Receive a tamper-proof digital credential with evidence-backed skills.',
    color: 'primary',
  },
];

export function HowItWorks() {
  return (
    <section className="section-padding relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-card/50 to-transparent" />
      
      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="text-center mb-16"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">How It Works</span>
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mt-4 mb-6">
            Three Steps to <span className="gradient-text">Verified Skills</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto">
            Our streamlined process transforms raw evidence into verified credentials in minutes.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8 relative">
          {/* Connection Line */}
          <div className="hidden md:block absolute top-24 left-1/4 right-1/4 h-0.5 bg-gradient-to-r from-primary via-accent to-primary opacity-30" />

          {steps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.2 }}
              className="relative"
            >
              <div className="glass-card p-8 text-center card-hover h-full">
                {/* Step Number */}
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 w-8 h-8 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center text-sm font-bold text-primary-foreground">
                  {index + 1}
                </div>

                {/* Icon */}
                <div className={`w-16 h-16 mx-auto mb-6 rounded-2xl bg-${step.color}/10 flex items-center justify-center`}>
                  <step.icon className={`w-8 h-8 ${step.color === 'primary' ? 'text-primary' : 'text-accent'}`} />
                </div>

                <h3 className="text-xl font-semibold mb-3">{step.title}</h3>
                <p className="text-muted-foreground text-sm">{step.description}</p>
              </div>

              {/* Arrow (between cards) */}
              {index < steps.length - 1 && (
                <div className="hidden md:flex absolute top-24 -right-4 z-10">
                  <ArrowRight className="w-8 h-8 text-primary/30" />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
