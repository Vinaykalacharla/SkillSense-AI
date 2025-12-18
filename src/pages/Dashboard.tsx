import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { ScoreCards } from '@/components/dashboard/ScoreCards';
import { SkillRadar } from '@/components/dashboard/SkillRadar';
import { RecentActivity } from '@/components/dashboard/RecentActivity';
import { RecommendedActions } from '@/components/dashboard/RecommendedActions';
import { VerificationTimeline } from '@/components/dashboard/VerificationTimeline';
import { Bell, Search, User } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function Dashboard() {
  return (
    <div className="min-h-screen bg-background">
      <DashboardSidebar />
      
      {/* Main Content */}
      <div className="pl-[260px]">
        {/* Top Bar */}
        <header className="h-16 border-b border-border/50 flex items-center justify-between px-6 sticky top-0 bg-background/80 backdrop-blur-xl z-30">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold">Dashboard</h1>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                placeholder="Search..."
                className="input-field pl-10 w-64"
              />
            </div>
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full" />
            </Button>
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <User className="w-5 h-5 text-primary-foreground" />
            </div>
          </div>
        </header>

        {/* Dashboard Content */}
        <main className="p-6">
          {/* Welcome */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <h2 className="text-2xl font-bold mb-2">
              Welcome back, <span className="gradient-text">Rahul</span> 👋
            </h2>
            <p className="text-muted-foreground">
              Your skill verification is 75% complete. Keep going!
            </p>
          </motion.div>

          {/* Score Cards */}
          <div className="mb-8">
            <ScoreCards />
          </div>

          {/* Main Grid */}
          <div className="grid lg:grid-cols-3 gap-6">
            {/* Left Column */}
            <div className="lg:col-span-2 space-y-6">
              <SkillRadar />
              <RecentActivity />
            </div>

            {/* Right Column */}
            <div className="space-y-6">
              <RecommendedActions />
              <VerificationTimeline />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
