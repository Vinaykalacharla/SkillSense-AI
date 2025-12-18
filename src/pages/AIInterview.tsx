import { useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import {
  Mic,
  MicOff,
  Video,
  VideoOff,
  Phone,
  MessageSquare,
  Brain,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

const transcript = [
  { speaker: 'AI', text: 'Tell me about your experience with React and state management.' },
  {
    speaker: 'You',
    text: "I've been working with React for about 2 years. I started with class components and moved to hooks. For state management, I've used both Redux and Zustand.",
  },
  {
    speaker: 'AI',
    text: 'Can you explain a challenging problem you solved using React?',
  },
];

const feedback = [
  {
    type: 'strength',
    icon: CheckCircle2,
    text: 'Clear articulation of technical concepts',
  },
  {
    type: 'strength',
    icon: CheckCircle2,
    text: 'Good use of specific examples',
  },
  {
    type: 'improvement',
    icon: AlertCircle,
    text: 'Try to provide more quantifiable outcomes',
  },
  {
    type: 'improvement',
    icon: AlertCircle,
    text: 'Slow down slightly for better clarity',
  },
];

export default function AIInterview() {
  const [micOn, setMicOn] = useState(true);
  const [videoOn, setVideoOn] = useState(true);
  const [isActive, setIsActive] = useState(true);

  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />

      <div className="pl-[260px]">
        <main className="p-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-6"
          >
            <h1 className="text-2xl font-bold mb-2">AI Interview Simulator</h1>
            <p className="text-muted-foreground">
              Practice technical interviews with our AI interviewer
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-3 gap-6">
            {/* Main Interview Area */}
            <div className="lg:col-span-2 space-y-6">
              {/* Video Area */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="glass-card p-6"
              >
                <div className="aspect-video bg-muted/30 rounded-xl relative overflow-hidden mb-4">
                  {/* AI Avatar Area */}
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-24 h-24 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center mx-auto mb-4 animate-pulse">
                        <Brain className="w-12 h-12 text-primary-foreground" />
                      </div>
                      <p className="text-lg font-medium">AI Interviewer</p>
                      <p className="text-sm text-muted-foreground">Listening...</p>
                    </div>
                  </div>

                  {/* User Video Preview */}
                  <div className="absolute bottom-4 right-4 w-32 h-24 bg-muted rounded-lg border border-border/50 overflow-hidden">
                    <div className="w-full h-full flex items-center justify-center bg-muted/50">
                      {videoOn ? (
                        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                          <span className="text-sm font-medium">RS</span>
                        </div>
                      ) : (
                        <VideoOff className="w-6 h-6 text-muted-foreground" />
                      )}
                    </div>
                  </div>

                  {/* Status Indicators */}
                  <div className="absolute top-4 left-4 flex items-center gap-2">
                    <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-red-500/20 text-red-400 text-xs">
                      <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                      Recording
                    </span>
                    <span className="px-3 py-1 rounded-full bg-primary/20 text-primary text-xs">
                      15:32
                    </span>
                  </div>
                </div>

                {/* Controls */}
                <div className="flex items-center justify-center gap-4">
                  <Button
                    variant={micOn ? 'default' : 'destructive'}
                    size="lg"
                    className="rounded-full w-14 h-14"
                    onClick={() => setMicOn(!micOn)}
                  >
                    {micOn ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
                  </Button>
                  <Button
                    variant={videoOn ? 'default' : 'destructive'}
                    size="lg"
                    className="rounded-full w-14 h-14"
                    onClick={() => setVideoOn(!videoOn)}
                  >
                    {videoOn ? <Video className="w-6 h-6" /> : <VideoOff className="w-6 h-6" />}
                  </Button>
                  <Button
                    variant="destructive"
                    size="lg"
                    className="rounded-full w-14 h-14"
                    onClick={() => setIsActive(false)}
                  >
                    <Phone className="w-6 h-6" />
                  </Button>
                </div>
              </motion.div>

              {/* Live Transcript */}
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.1 }}
                className="glass-card p-6"
              >
                <div className="flex items-center gap-2 mb-4">
                  <MessageSquare className="w-5 h-5 text-primary" />
                  <h3 className="font-semibold">Live Transcript</h3>
                </div>
                <div className="space-y-4 max-h-[300px] overflow-y-auto">
                  {transcript.map((item, index) => (
                    <div
                      key={index}
                      className={`flex gap-3 ${
                        item.speaker === 'You' ? 'flex-row-reverse' : ''
                      }`}
                    >
                      <div
                        className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                          item.speaker === 'AI'
                            ? 'bg-primary/20'
                            : 'bg-accent/20'
                        }`}
                      >
                        {item.speaker === 'AI' ? (
                          <Brain className="w-4 h-4 text-primary" />
                        ) : (
                          <span className="text-xs">RS</span>
                        )}
                      </div>
                      <div
                        className={`p-3 rounded-xl max-w-[80%] ${
                          item.speaker === 'AI'
                            ? 'bg-muted/50'
                            : 'bg-primary/10'
                        }`}
                      >
                        <p className="text-sm">{item.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>
            </div>

            {/* Right Panel */}
            <div className="space-y-6">
              {/* Real-time Metrics */}
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.2 }}
                className="glass-card p-6"
              >
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-5 h-5 text-accent" />
                  <h3 className="font-semibold">Real-time Analysis</h3>
                </div>
                <div className="space-y-4">
                  {[
                    { label: 'Confidence', value: 78, color: 'primary' },
                    { label: 'Clarity', value: 85, color: 'accent' },
                    { label: 'Pace', value: 70, color: 'primary' },
                    { label: 'Technical Depth', value: 82, color: 'accent' },
                  ].map((metric, index) => (
                    <div key={index}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-muted-foreground">{metric.label}</span>
                        <span className="font-medium">{metric.value}%</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${metric.value}%` }}
                          transition={{ duration: 1, delay: index * 0.1 }}
                          className={`h-full rounded-full ${
                            metric.color === 'primary'
                              ? 'bg-gradient-to-r from-primary to-primary/60'
                              : 'bg-gradient-to-r from-accent to-accent/60'
                          }`}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Live Feedback */}
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.3 }}
                className="glass-card p-6"
              >
                <h3 className="font-semibold mb-4">Live Feedback</h3>
                <div className="space-y-3">
                  {feedback.map((item, index) => (
                    <div
                      key={index}
                      className={`flex items-start gap-3 p-3 rounded-xl ${
                        item.type === 'strength' ? 'bg-green-500/10' : 'bg-amber-500/10'
                      }`}
                    >
                      <item.icon
                        className={`w-5 h-5 flex-shrink-0 ${
                          item.type === 'strength' ? 'text-green-400' : 'text-amber-400'
                        }`}
                      />
                      <span className="text-sm">{item.text}</span>
                    </div>
                  ))}
                </div>
              </motion.div>

              {/* Quick Tips */}
              <motion.div
                initial={{ opacity: 0, x: 30 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.6, delay: 0.4 }}
                className="glass-card p-6"
              >
                <h3 className="font-semibold mb-4">💡 Tips</h3>
                <ul className="space-y-2 text-sm text-muted-foreground">
                  <li>• Use the STAR method for behavioral questions</li>
                  <li>• Provide specific examples from your experience</li>
                  <li>• It's okay to pause and think before answering</li>
                  <li>• Ask clarifying questions if needed</li>
                </ul>
              </motion.div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
