import React, { useState } from 'react';
import type { ActiveTab } from '../types';

interface HeaderProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  onNewInspection: () => void;
  historyCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  onTabChange,
  onNewInspection,
  historyCount,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleTabClick = (tab: ActiveTab) => {
    setMobileMenuOpen(false);
    onTabChange(tab);
    if (tab === 'about') {
      const element = document.getElementById('how-it-works');
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    } else {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  return (
    <header className="navbar-root">
      <div className="navbar-container">
        {/* Brand Logo & Wordmark */}
        <a
          href="#"
          className="navbar-brand"
          onClick={(e) => {
            e.preventDefault();
            handleTabClick('inspect');
          }}
        >
          <div className="brand-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              <path d="m9 12 2 2 4-4"/>
            </svg>
          </div>
          <span className="brand-text">LegalCheck</span>
        </a>

        {/* Navigation Tabs */}
        <nav className={`navbar-nav ${mobileMenuOpen ? 'open' : ''}`}>
          <button
            type="button"
            className={`nav-link ${activeTab === 'inspect' ? 'active' : ''}`}
            onClick={() => handleTabClick('inspect')}
          >
            Inspect
          </button>
          <button
            type="button"
            className={`nav-link ${activeTab === 'history' ? 'active' : ''}`}
            onClick={() => handleTabClick('history')}
          >
            History
            {historyCount > 0 && <span className="nav-badge">{historyCount}</span>}
          </button>
          <button
            type="button"
            className={`nav-link ${activeTab === 'about' ? 'active' : ''}`}
            onClick={() => handleTabClick('about')}
          >
            About
          </button>
        </nav>

        {/* Action Button & Mobile Toggle */}
        <div className="navbar-actions">
          <button
            type="button"
            className="btn-nav-primary"
            onClick={() => {
              setMobileMenuOpen(false);
              onNewInspection();
            }}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
            New inspection
          </button>

          <button
            type="button"
            className="mobile-menu-toggle"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            aria-label="Toggle Navigation Menu"
          >
            {mobileMenuOpen ? (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="18" x2="20" y2="18"/></svg>
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
