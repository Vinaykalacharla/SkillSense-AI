import { motion } from 'framer-motion';
import { Users, Target, Award, TrendingUp } from 'lucide-react';

export function AboutSection() {
  return (
    <section id="about" className="section-padding relative overflow-hidden">
      <div className="container-custom">
        <div className="max-w-4xl mx-auto text-center mb-16">
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-3xl sm:text-4xl md:text-5xl font-bold mb-6"
          >
            Revolutionizing Skill Verification with{' '}
            <span className="gradient-text">AI Technology</span>
          </motion.h2>
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
            className="text-lg text-muted-foreground max-w-2xl mx-auto"
          >
            We're bridging the gap between education and employment by providing
            verifiable proof of skills that employers can trust.
          </motion.p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {[
            {
              icon: Users,
              title: 'For Students',
              description: 'Showcase your real skills with AI-verified credentials that stand out to employers.'
            },
            {
              icon: Target,
              title: 'For Employers',
              description: 'Find truly skilled candidates with confidence using our advanced verification system.'
            },
            {
              icon: Award,
              title: 'For Universities',
              description: 'Partner with us to provide your students with industry-recognized skill verification.'
            },
            {
              icon: TrendingUp,
              title: 'For Recruiters',
              description: 'Streamline your hiring process with reliable, AI-powered skill assessments.'
            }
          ].map((item, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              className="glass-card p-6 text-center group hover:scale-105 transition-transform"
            >
              <div className="w-12 h-12 mx-auto mb-4 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
                <item.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
              <p className="text-muted-foreground">{item.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
