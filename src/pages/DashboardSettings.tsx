import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { DashboardSidebar } from '@/components/dashboard/Sidebar';
import { Settings, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

export default function DashboardSettings() {
  const [profile, setProfile] = useState<Record<string, any> | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      return;
    }
    fetch('http://127.0.0.1:8000/api/accounts/profile/', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => res.json())
      .then((data) => setProfile(data?.user || null))
      .catch(() => setProfile(null));
  }, []);

  const handleSave = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token || !profile) {
      return;
    }
    setSaving(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/accounts/profile/update/', {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(profile),
      });
      if (res.ok) {
        const data = await res.json();
        setProfile(data?.user || profile);
      }
    } finally {
      setSaving(false);
    }
  };

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
            <h1 className="text-2xl font-bold mb-2">Settings</h1>
            <p className="text-muted-foreground">Profile and preferences</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="glass-card p-6"
          >
            {profile ? (
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-4">
                  <Input
                    placeholder="Full name"
                    value={profile.full_name || ''}
                    onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                  />
                  <Input
                    placeholder="Gender"
                    value={profile.gender || ''}
                    onChange={(e) => setProfile({ ...profile, gender: e.target.value })}
                  />
                  <Input
                    placeholder="Phone number"
                    value={profile.phone_number || ''}
                    onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
                  />
                  <Input
                    placeholder="College"
                    value={profile.college || ''}
                    onChange={(e) => setProfile({ ...profile, college: e.target.value })}
                  />
                  <Input
                    placeholder="Course"
                    value={profile.course || ''}
                    onChange={(e) => setProfile({ ...profile, course: e.target.value })}
                  />
                  <Input
                    placeholder="Branch"
                    value={profile.branch || ''}
                    onChange={(e) => setProfile({ ...profile, branch: e.target.value })}
                  />
                  <Input
                    placeholder="Year of study"
                    value={profile.year_of_study || ''}
                    onChange={(e) => setProfile({ ...profile, year_of_study: e.target.value })}
                  />
                  <Input
                    placeholder="CGPA"
                    value={profile.cgpa || ''}
                    onChange={(e) => setProfile({ ...profile, cgpa: e.target.value })}
                  />
                  <Textarea
                    placeholder="Skills (comma-separated)"
                    value={profile.student_skills || ''}
                    onChange={(e) => setProfile({ ...profile, student_skills: e.target.value })}
                    rows={2}
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <Input
                    placeholder="GitHub URL"
                    value={profile.github_link || ''}
                    onChange={(e) => setProfile({ ...profile, github_link: e.target.value })}
                  />
                  <Input
                    placeholder="LeetCode URL"
                    value={profile.leetcode_link || ''}
                    onChange={(e) => setProfile({ ...profile, leetcode_link: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn URL"
                    value={profile.linkedin_link || ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_link: e.target.value })}
                  />
                  <Input
                    placeholder="CodeChef URL"
                    value={profile.codechef_link || ''}
                    onChange={(e) => setProfile({ ...profile, codechef_link: e.target.value })}
                  />
                  <Input
                    placeholder="HackerRank URL"
                    value={profile.hackerrank_link || ''}
                    onChange={(e) => setProfile({ ...profile, hackerrank_link: e.target.value })}
                  />
                  <Input
                    placeholder="Codeforces URL"
                    value={profile.codeforces_link || ''}
                    onChange={(e) => setProfile({ ...profile, codeforces_link: e.target.value })}
                  />
                  <Input
                    placeholder="GeeksforGeeks URL"
                    value={profile.gfg_link || ''}
                    onChange={(e) => setProfile({ ...profile, gfg_link: e.target.value })}
                  />
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <Input
                    placeholder="LinkedIn headline"
                    value={profile.linkedin_headline || ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_headline: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn experience count"
                    value={profile.linkedin_experience_count ?? ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_experience_count: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn skills count"
                    value={profile.linkedin_skill_count ?? ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_skill_count: e.target.value })}
                  />
                  <Input
                    placeholder="LinkedIn certifications count"
                    value={profile.linkedin_cert_count ?? ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_cert_count: e.target.value })}
                  />
                  <Textarea
                    placeholder="LinkedIn about summary"
                    value={profile.linkedin_about || ''}
                    onChange={(e) => setProfile({ ...profile, linkedin_about: e.target.value })}
                    rows={3}
                    className="md:col-span-2"
                  />
                </div>

                <Button onClick={handleSave} disabled={saving}>
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Changes'}
                </Button>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                <Settings className="w-10 h-10 mb-3 text-primary" />
                No settings available yet
              </div>
            )}
          </motion.div>
        </main>
      </div>
    </div>
  );
}
