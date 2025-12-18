import { motion } from 'framer-motion';
import { Code, FileText, Video, CheckCircle2, Clock } from 'lucide-react';

const activities = [
  {
    icon: Code,
    title: 'GitHub Repository Analyzed',
    description: 'react-portfolio analyzed with 12 skills extracted',
    time: '2 hours ago',
    status: 'completed',
  },
  {
    icon: FileText,
    title: 'Resume Verified',
    description: 'PDF document processed with NLP analysis',
    time: '5 hours ago',
    status: 'completed',
  },
  {
    icon: Video,
    title: 'Video Interview Processing',
    description: 'Communication skills being analyzed',
    time: '1 day ago',
    status: 'pending',
  },
  {
    icon: CheckCircle2,
    title: 'Skill Badge Earned',
    description: 'React.js Intermediate verified',
    time: '2 days ago',
    status: 'completed',
  },
];

export function RecentActivity() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="glass-card p-6"
    >
      <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
      <div className="space-y-4">
        {activities.map((activity, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
            className="flex items-start gap-4 p-3 rounded-xl hover:bg-muted/30 transition-colors"
          >
            <div
              className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                activity.status === 'completed' ? 'bg-primary/10' : 'bg-accent/10'
              }`}
            >
              <activity.icon
                className={`w-5 h-5 ${
                  activity.status === 'completed' ? 'text-primary' : 'text-accent'
                }`}
              />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm truncate">{activity.title}</span>
                {activity.status === 'pending' && (
                  <span className="flex items-center gap-1 text-xs text-accent bg-accent/10 px-2 py-0.5 rounded-full">
                    <Clock className="w-3 h-3" />
                    Processing
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground truncate">{activity.description}</p>
              <span className="text-xs text-muted-foreground">{activity.time}</span>
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
