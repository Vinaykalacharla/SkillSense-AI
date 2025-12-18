import { motion } from 'framer-motion';
import { ArrowRight, Mic, Upload, Target, BookOpen } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from 'react-router-dom';

const recommendations = [
  {
    icon: Mic,
    title: 'Take AI Interview',
    description: 'Practice technical interviews to boost your communication score',
    href: '/dashboard/interview',
    priority: 'high',
  },
  {
    icon: Upload,
    title: 'Upload More Projects',
    description: 'Add 2 more projects to complete your portfolio',
    href: '/dashboard/submit',
    priority: 'medium',
  },
  {
    icon: Target,
    title: 'Complete Assessment',
    description: 'Data Structures quiz available',
    href: '/dashboard/assessments',
    priority: 'medium',
  },
  {
    icon: BookOpen,
    title: 'Review Roadmap',
    description: 'Check your 90-day personalized learning plan',
    href: '/dashboard/roadmap',
    priority: 'low',
  },
];

const priorityColors = {
  high: 'border-l-red-500',
  medium: 'border-l-amber-500',
  low: 'border-l-green-500',
};

export function RecommendedActions() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: 0.3 }}
      className="glass-card p-6"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Recommended Actions</h3>
        <span className="text-xs text-muted-foreground">AI Suggestions</span>
      </div>
      
      <div className="space-y-3">
        {recommendations.map((item, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.4, delay: index * 0.1 }}
          >
            <Link
              to={item.href}
              className={`block p-4 rounded-xl bg-muted/30 hover:bg-muted/50 border-l-4 ${
                priorityColors[item.priority]
              } transition-all group`}
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <item.icon className="w-5 h-5 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{item.title}</div>
                  <p className="text-sm text-muted-foreground truncate">
                    {item.description}
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
              </div>
            </Link>
          </motion.div>
        ))}
      </div>

      <Button variant="ghost" className="w-full mt-4">
        View All Recommendations
      </Button>
    </motion.div>
  );
}
