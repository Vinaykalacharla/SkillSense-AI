import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Menu, X, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

const navItems = [
  { label: 'Home', href: '/', type: 'link' },
  { label: 'About', href: '#about', type: 'scroll' },
  { label: 'Features', href: '#features', type: 'scroll' },
  { label: 'Dashboard', href: '/dashboard', type: 'link' },
  { label: 'Login', href: '/login', type: 'link' },
  { label: 'Contact Us', href: '#contact-us', type: 'scroll' },
  { label: 'Get Started', href: '/dashboard', type: 'link' },
];

const Navbar = () => {
  const [isOpen, setIsOpen] = useState(false);
  const location = useLocation();

  const handleNavClick = (href: string) => {
    setIsOpen(false);
    if (href.startsWith('#')) {
      const element = document.querySelector(href);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
  };

  return (
    <header className="fixed top-0 w-full z-50 bg-background/80 backdrop-blur-md border-b">
      <nav className="container-custom">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-2">
            <img src="https://i.ibb.co/M51qFRs5/Screenshot-2025-12-18-125743-removebg-preview.png" alt="Skillsence AI Logo" className="w-8 h-8" />
            <span className="text-xl font-bold gradient-text">Skillsence AI</span>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-2 ml-auto">
            {navItems.map((item) => {
              if (item.type === 'scroll') {
                return (
                  <Button
                    key={item.label}
                    variant="ghost"
                    onClick={() => handleNavClick(item.href)}
                  >
                    {item.label}
                  </Button>
                );
              } else {
                return (
                  <Link key={item.label} to={item.href}>
                    <Button variant="ghost">
                      {item.label}
                    </Button>
                  </Link>
                );
              }
            })}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Toggle menu"
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isOpen && (
          <div className="md:hidden py-4 border-t">
            <div className="flex flex-col space-y-4">
              {navItems.map((item) => {
                if (item.type === 'scroll') {
                  return (
                    <Button
                      key={item.label}
                      variant="ghost"
                      onClick={() => handleNavClick(item.href)}
                      className="w-full justify-start"
                    >
                      {item.label}
                    </Button>
                  );
                } else {
                  return (
                    <Link key={item.label} to={item.href} onClick={() => setIsOpen(false)}>
                      <Button variant="ghost" className="w-full justify-start">
                        {item.label}
                      </Button>
                    </Link>
                  );
                }
              })}
            </div>
          </div>
        )}
      </nav>
    </header>
  );
};

export { Navbar };
