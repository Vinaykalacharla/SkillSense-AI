import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import SkillPassport from "./pages/SkillPassport";
import AIInterview from "./pages/AIInterview";
import RecruiterDashboard from "./pages/RecruiterDashboard";
import UniversityDashboard from "./pages/UniversityDashboard";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/student" element={<Login />} />
          <Route path="/university" element={<Login />} />
          <Route path="/recruiter" element={<Login />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/passport" element={<SkillPassport />} />
          <Route path="/dashboard/interview" element={<AIInterview />} />
          <Route path="/recruiter/dashboard" element={<RecruiterDashboard />} />
          <Route path="/university/dashboard" element={<UniversityDashboard />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
