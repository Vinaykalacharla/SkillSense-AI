import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { GraduationCap, ArrowLeft, Link2, BookOpen, BadgeCheck, Sparkles, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';

export default function StudentRegister() {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    full_name: '',
    gender: '',
    phone_number: '',
    email: '',
    password: '',
    college: '',
    course: '',
    branch: '',
    year_of_study: '',
    cgpa: '',
    student_skills: '',
    github_link: '',
    leetcode_link: '',
    linkedin_link: '',
    linkedin_headline: '',
    linkedin_about: '',
    linkedin_experience_count: '',
    linkedin_skill_count: '',
    linkedin_cert_count: '',
    codechef_link: '',
    hackerrank_link: '',
    codeforces_link: '',
    gfg_link: '',
  });
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [skillInput, setSkillInput] = useState('');
  const [skills, setSkills] = useState<string[]>([]);
  const [genderPreset, setGenderPreset] = useState('');
  const [genderCustom, setGenderCustom] = useState('');
  const [yearPreset, setYearPreset] = useState('');
  const [yearCustom, setYearCustom] = useState('');

  const [skillSuggestions, setSkillSuggestions] = useState<string[]>([]);

  const normalizeGender = (value: string) => {
    const normalized = value.trim().toLowerCase();
    if (!normalized) {
      return '';
    }
    const male = new Set(['m', 'male', 'man', 'boy']);
    const female = new Set(['f', 'female', 'woman', 'girl']);
    const other = new Set(['other', 'nonbinary', 'non-binary', 'nb']);
    const prefer = new Set(['na', 'n/a', 'none', 'prefer not to say', 'prefer not']);

    if (male.has(normalized)) {
      return 'Male';
    }
    if (female.has(normalized)) {
      return 'Female';
    }
    if (other.has(normalized)) {
      return 'Other';
    }
    if (prefer.has(normalized)) {
      return 'Prefer not to say';
    }
    return value.trim();
  };

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/skills/skill-suggestions/')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setSkillSuggestions(data);
        }
      })
      .catch(() => {
        setSkillSuggestions([]);
      });
  }, []);

  const normalizeSkill = (value: string) => value.trim();

  const addSkill = (value: string) => {
    const trimmed = normalizeSkill(value);
    if (!trimmed) {
      return;
    }
    const canonical =
      skillSuggestions.find(
        (skill) => skill.toLowerCase() === trimmed.toLowerCase()
      ) || trimmed;
    const exists = skills.some((skill) => skill.toLowerCase() === canonical.toLowerCase());
    if (!exists) {
      setSkills([...skills, canonical]);
    }
    setSkillInput('');
  };

  const removeSkill = (value: string) => {
    setSkills(skills.filter((skill) => skill !== value));
  };

  const handleGenderSelect = (value: string) => {
    setGenderPreset(value);
    if (value !== 'Self describe') {
      setGenderCustom('');
    }
    setFormData((prev) => ({
      ...prev,
      gender: value === 'Self describe' ? '' : value,
    }));
  };

  const handleYearSelect = (value: string) => {
    setYearPreset(value);
    if (value !== 'Other') {
      setYearCustom('');
    }
    setFormData((prev) => ({
      ...prev,
      year_of_study: value === 'Other' ? '' : value,
    }));
  };

  useEffect(() => {
    if (genderPreset === 'Self describe') {
      setFormData((prev) => ({
        ...prev,
        gender: genderCustom,
      }));
    }
  }, [genderCustom, genderPreset]);

  useEffect(() => {
    if (yearPreset === 'Other') {
      setFormData((prev) => ({
        ...prev,
        year_of_study: yearCustom,
      }));
    }
  }, [yearCustom, yearPreset]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    const username = formData.email.split('@')[0] || formData.full_name.replace(/\s+/g, '').toLowerCase();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/accounts/signup/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          student_skills: skills.join(', '),
          gender: normalizeGender(formData.gender),
          username,
          role: 'student',
        }),
      });

      const data = await response.json();

      if (response.ok) {
        localStorage.setItem('accessToken', data.access);
        localStorage.setItem('refreshToken', data.refresh);
        localStorage.setItem('userRole', data.user.role);
        localStorage.setItem('user', JSON.stringify(data.user));
        navigate('/dashboard');
      } else {
        setError(data.error || 'Registration failed');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-background to-accent/10" />
        <div className="absolute -top-32 -right-24 w-[420px] h-[420px] rounded-full bg-primary/20 blur-3xl" />
        <div className="absolute -bottom-32 -left-24 w-[420px] h-[420px] rounded-full bg-accent/20 blur-3xl" />
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="relative z-10 max-w-6xl mx-auto px-4 py-12"
        >
          <div className="grid lg:grid-cols-[320px_1fr] gap-8">
            <div className="space-y-6">
              <div className="glass-card p-6">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary to-accent flex items-center justify-center mb-4">
                  <GraduationCap className="w-7 h-7 text-primary-foreground" />
                </div>
                <h1 className="text-3xl font-bold mb-2">Student Registration</h1>
                <p className="text-sm text-muted-foreground">
                  Build a verified profile that syncs skills with real platform activity.
                </p>
                <div className="mt-6 space-y-3 text-xs text-muted-foreground">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary" />
                    Real platform analysis
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-accent" />
                    Evidence-backed scores
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-primary/50" />
                    Skill passport generation
                  </div>
                </div>
              </div>

              <div className="glass-card p-6">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <BadgeCheck className="w-4 h-4 text-accent" />
                  Verification Note
                </div>
                <p className="mt-3 text-xs text-muted-foreground">
                  We normalize your skills and links to match platform evidence, so your scores stay accurate.
                </p>
              </div>

              <button
                onClick={() => navigate('/student')}
                className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-2"
              >
                <ArrowLeft className="w-4 h-4" />
                Back to Login
              </button>
            </div>

            <Card className="glass-card">
              <CardHeader className="border-b border-border/50">
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-xl">Profile Build</CardTitle>
                    <CardDescription>Complete each block for accurate scoring</CardDescription>
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <Sparkles className="w-4 h-4 text-primary" />
                    2026-ready
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-6">
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <UserPlus className="w-4 h-4 text-primary" />
                      <h3 className="text-sm font-semibold">Personal Details</h3>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="full_name">Full Name</Label>
                        <Input
                          id="full_name"
                          value={formData.full_name}
                          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                          placeholder="Enter your full name"
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="gender">Gender</Label>
                        <div className="flex flex-wrap gap-2">
                          {['Male', 'Female', 'Non-binary', 'Prefer not to say', 'Self describe'].map((option) => {
                            const active = genderPreset === option;
                            return (
                              <button
                                key={option}
                                type="button"
                                onClick={() => handleGenderSelect(option)}
                                className={`px-3 py-2 rounded-full text-xs font-medium border transition ${
                                  active
                                    ? 'border-primary text-primary bg-primary/10'
                                    : 'border-border/60 text-muted-foreground hover:text-foreground'
                                }`}
                              >
                                {option}
                              </button>
                            );
                          })}
                        </div>
                        {genderPreset === 'Self describe' && (
                          <Input
                            id="gender"
                            value={genderCustom}
                            onChange={(e) => setGenderCustom(e.target.value)}
                            placeholder="Share in your own words"
                          />
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="phone_number">Phone Number</Label>
                        <Input
                          id="phone_number"
                          value={formData.phone_number}
                          onChange={(e) => setFormData({ ...formData, phone_number: e.target.value })}
                          placeholder="Phone number"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="email">Email</Label>
                        <Input
                          id="email"
                          type="email"
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          placeholder="Email address"
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="password">Password</Label>
                        <Input
                          id="password"
                          type="password"
                          value={formData.password}
                          onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                          placeholder="Create a password"
                          required
                        />
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <BookOpen className="w-4 h-4 text-accent" />
                      <h3 className="text-sm font-semibold">Academics</h3>
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="college">College</Label>
                        <Input
                          id="college"
                          value={formData.college}
                          onChange={(e) => setFormData({ ...formData, college: e.target.value })}
                          placeholder="College/University"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="course">Course</Label>
                        <Input
                          id="course"
                          value={formData.course}
                          onChange={(e) => setFormData({ ...formData, course: e.target.value })}
                          placeholder="Course name"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="branch">Branch</Label>
                        <Input
                          id="branch"
                          value={formData.branch}
                          onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                          placeholder="Branch or specialization"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="year_of_study">Year of Study</Label>
                        <div className="flex flex-wrap gap-2">
                          {['1st Year', '2nd Year', '3rd Year', '4th Year', 'Postgrad', 'Other'].map((option) => {
                            const active = yearPreset === option;
                            return (
                              <button
                                key={option}
                                type="button"
                                onClick={() => handleYearSelect(option)}
                                className={`px-3 py-2 rounded-full text-xs font-medium border transition ${
                                  active
                                    ? 'border-accent text-accent bg-accent/10'
                                    : 'border-border/60 text-muted-foreground hover:text-foreground'
                                }`}
                              >
                                {option}
                              </button>
                            );
                          })}
                        </div>
                        {yearPreset === 'Other' && (
                          <Input
                            id="year_of_study"
                            value={yearCustom}
                            onChange={(e) => setYearCustom(e.target.value)}
                            placeholder="Tell us your year"
                          />
                        )}
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="cgpa">CGPA</Label>
                        <Input
                          id="cgpa"
                          value={formData.cgpa}
                          onChange={(e) => setFormData({ ...formData, cgpa: e.target.value })}
                          placeholder="e.g. 8.2"
                        />
                      </div>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-border/60 bg-card/60 p-5">
                    <div className="flex items-center gap-2 mb-4">
                      <Link2 className="w-4 h-4 text-primary" />
                      <h3 className="text-sm font-semibold">Skills & Platforms</h3>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="student_skills">Skills</Label>
                      <div className="relative">
                        <Input
                          id="student_skills"
                          value={skillInput}
                          onChange={(e) => setSkillInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              e.preventDefault();
                              addSkill(skillInput);
                            }
                            if (e.key === ',' && skillInput.trim()) {
                              e.preventDefault();
                              addSkill(skillInput);
                            }
                          }}
                          placeholder="Type a skill and press Enter"
                        />
                        {skillInput.trim() && (
                          <div className="absolute z-20 mt-2 w-full rounded-xl border border-border/60 bg-background shadow-lg">
                            {skillSuggestions
                              .filter((skill) =>
                                skill.toLowerCase().startsWith(skillInput.trim().toLowerCase())
                              )
                              .slice(0, 6)
                              .map((skill) => (
                                <button
                                  type="button"
                                  key={skill}
                                  className="w-full text-left px-3 py-2 text-sm hover:bg-muted"
                                  onClick={() => addSkill(skill)}
                                >
                                  {skill}
                                </button>
                              ))}
                            {skillSuggestions.filter((skill) =>
                              skill.toLowerCase().startsWith(skillInput.trim().toLowerCase())
                            ).length === 0 && (
                              <div className="px-3 py-2 text-sm text-muted-foreground">
                                Press Enter to add "{skillInput.trim()}"
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      {skills.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {skills.map((skill) => (
                            <button
                              type="button"
                              key={skill}
                              onClick={() => removeSkill(skill)}
                              className="px-3 py-1 rounded-full bg-primary/10 text-primary text-xs hover:bg-primary/20"
                            >
                              {skill}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                    <div className="grid md:grid-cols-2 gap-4 mt-4">
                      {[
                        { id: 'github_link', label: 'GitHub', placeholder: 'GitHub profile URL' },
                        { id: 'leetcode_link', label: 'LeetCode', placeholder: 'LeetCode profile URL' },
                        { id: 'linkedin_link', label: 'LinkedIn', placeholder: 'LinkedIn profile URL' },
                        { id: 'codechef_link', label: 'CodeChef', placeholder: 'CodeChef profile URL' },
                        { id: 'hackerrank_link', label: 'HackerRank', placeholder: 'HackerRank profile URL' },
                        { id: 'codeforces_link', label: 'Codeforces', placeholder: 'Codeforces profile URL' },
                        { id: 'gfg_link', label: 'GeeksforGeeks', placeholder: 'GeeksforGeeks profile URL' },
                      ].map((field) => (
                        <div key={field.id} className="space-y-2">
                          <Label htmlFor={field.id}>{field.label}</Label>
                          <Input
                            id={field.id}
                            value={(formData as Record<string, string>)[field.id]}
                            onChange={(e) => setFormData({ ...formData, [field.id]: e.target.value })}
                            placeholder={field.placeholder}
                          />
                        </div>
                      ))}
                    </div>

                    <div className="mt-6 rounded-2xl border border-border/60 bg-muted/30 p-4">
                      <div className="flex items-center justify-between mb-3">
                        <div>
                          <div className="text-sm font-semibold">LinkedIn Snapshot</div>
                          <div className="text-xs text-muted-foreground">
                            Add quick proof points used for LinkedIn scoring.
                          </div>
                        </div>
                        <span className="text-[10px] uppercase tracking-wide text-primary">Manual</span>
                      </div>
                      <div className="grid md:grid-cols-2 gap-4">
                        <div className="space-y-2 md:col-span-2">
                          <Label htmlFor="linkedin_headline">Headline</Label>
                          <Input
                            id="linkedin_headline"
                            value={formData.linkedin_headline}
                            onChange={(e) => setFormData({ ...formData, linkedin_headline: e.target.value })}
                            placeholder="e.g. Backend Developer | Python | Django"
                          />
                        </div>
                        <div className="space-y-2 md:col-span-2">
                          <Label htmlFor="linkedin_about">About Summary</Label>
                          <Textarea
                            id="linkedin_about"
                            value={formData.linkedin_about}
                            onChange={(e) => setFormData({ ...formData, linkedin_about: e.target.value })}
                            placeholder="Short summary from your LinkedIn profile"
                            rows={3}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="linkedin_experience_count">Experience Count</Label>
                          <Input
                            id="linkedin_experience_count"
                            type="number"
                            min={0}
                            value={formData.linkedin_experience_count}
                            onChange={(e) => setFormData({ ...formData, linkedin_experience_count: e.target.value })}
                            placeholder="e.g. 2"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="linkedin_skill_count">Skills Listed</Label>
                          <Input
                            id="linkedin_skill_count"
                            type="number"
                            min={0}
                            value={formData.linkedin_skill_count}
                            onChange={(e) => setFormData({ ...formData, linkedin_skill_count: e.target.value })}
                            placeholder="e.g. 12"
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="linkedin_cert_count">Certifications</Label>
                          <Input
                            id="linkedin_cert_count"
                            type="number"
                            min={0}
                            value={formData.linkedin_cert_count}
                            onChange={(e) => setFormData({ ...formData, linkedin_cert_count: e.target.value })}
                            placeholder="e.g. 1"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  {error && <div className="text-sm text-destructive text-center">{error}</div>}

                  <Button type="submit" className="w-full" disabled={isSubmitting}>
                    {isSubmitting ? 'Creating Account...' : 'Create Account'}
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
