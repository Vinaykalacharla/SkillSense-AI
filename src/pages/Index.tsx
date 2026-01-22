import { useEffect, useState } from 'react';
import { Navbar } from '@/components/layout/Navbar';
import { Footer } from '@/components/layout/Footer';
import { HeroSection } from '@/components/landing/HeroSection';
import { FeaturesSection } from '@/components/landing/FeaturesSection';
import { UserTypes } from '@/components/landing/UserTypes';
import { Testimonials } from '@/components/landing/Testimonials';
import { AboutSection } from '@/components/landing/AboutSection';
import { CTASection } from '@/components/landing/CTASection';

const Index = () => {
  const [content, setContent] = useState<Record<string, any>>({});

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/content/landing/')
      .then((res) => res.json())
      .then((data) => setContent(data || {}))
      .catch(() => setContent({}));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <Navbar />
      <main>
        <HeroSection content={content.hero} />
        <FeaturesSection
          features={content.features || []}
          dataTypes={content.data_types || []}
        />
        <UserTypes userTypes={content.user_types || []} />
        <Testimonials testimonials={content.testimonials || []} />
        <AboutSection content={content.about} />
        <CTASection content={content.contact} />
      </main>
      <Footer />
    </div>
  );
};

export default Index;
