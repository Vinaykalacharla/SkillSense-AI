import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, Mail, Phone } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

export function CTASection() {
  return (
    <section id="contact-us" className="section-padding relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-r from-primary/10 via-transparent to-accent/10" />
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-primary/10 rounded-full blur-3xl" />
      
      <div className="container-custom relative z-10">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="glass-card p-8 md:p-12 lg:p-16 text-center max-w-4xl mx-auto"
        >
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 mb-6">
            <Sparkles className="w-4 h-4 text-primary" />
            <span className="text-sm font-medium text-primary">Contact Us</span>
          </div>

          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold mb-6">
            Get in Touch with{' '}
            <span className="gradient-text">Skillsence AI</span>
          </h2>

          <p className="text-muted-foreground text-lg mb-8 max-w-2xl mx-auto">
            Have questions or need assistance? We're here to help you on your journey to verified skills and career success.
          </p>

          <div className="flex flex-col gap-6 justify-center items-center">
            <div className="flex items-center gap-4 text-lg">
              <Mail className="w-6 h-6 text-primary" />
              <span>skillssenceai@gmail.com</span>
            </div>
            <div className="flex items-center gap-4 text-lg">
              <Phone className="w-6 h-6 text-primary" />
              <span>+91 6300063289</span>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mt-8">
            <Link to="/dashboard">
              <Button variant="hero" size="xl">
                Get Started Free
                <ArrowRight className="w-5 h-5" />
              </Button>
            </Link>
            <Button variant="glass" size="xl">
              Schedule Demo
            </Button>
          </div>

          <p className="text-muted-foreground text-sm mt-6">
            No credit card required • Free forever plan available
          </p>
        </motion.div>
      </div>
    </section>
  );
}
