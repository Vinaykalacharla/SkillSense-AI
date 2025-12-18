import { motion } from 'framer-motion';
import { CheckCircle2, Circle, Clock } from 'lucide-react';

const timelineItems = [
  {
    title: 'Profile Created',
    date: 'Jan 15, 2025',
    status: 'completed',
  },
  {
    title: 'First Code Upload',
    date: 'Jan 18, 2025',
    status: 'completed',
  },
  {
    title: 'Skills Extracted',
    date: 'Jan 18, 2025',
    status: 'completed',
  },
  {
    title: 'AI Interview Completed',
    date: 'Jan 22, 2025',
    status: 'completed',
  },
  {
    title: 'Document Verification',
    date: 'In Progress',
    status: 'current',
  },
  {
    title: 'Skill Passport Ready',
    date: 'Pending',
    status: 'pending',
  },
];

export function VerificationTimeline() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.4 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-6">Verification Timeline</h3>
      
      <div className="relative">
        {/* Vertical Line */}
        <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gradient-to-b from-primary via-accent to-muted" />

        <div className="space-y-6">
          {timelineItems.map((item, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: index * 0.1 }}
              className="flex items-start gap-4 relative"
            >
              {/* Icon */}
              <div className="relative z-10 w-8 h-8 rounded-full flex items-center justify-center bg-background">
                {item.status === 'completed' ? (
                  <CheckCircle2 className="w-6 h-6 text-primary" />
                ) : item.status === 'current' ? (
                  <Clock className="w-6 h-6 text-accent animate-pulse" />
                ) : (
                  <Circle className="w-6 h-6 text-muted-foreground" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 pb-2">
                <div
                  className={`font-medium text-sm ${
                    item.status === 'pending' ? 'text-muted-foreground' : ''
                  }`}
                >
                  {item.title}
                </div>
                <div className="text-xs text-muted-foreground">{item.date}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
