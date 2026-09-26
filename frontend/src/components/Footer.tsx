import React from 'react';

export const Footer: React.FC = () => {
  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <footer className="footer-root">
      <div className="footer-container">
        <div className="footer-top-row">
          <div className="footer-brand-block">
            <div className="footer-logo">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="m9 12 2 2 4-4"/>
              </svg>
              <span>LegalCheck</span>
            </div>
            <p className="footer-brand-desc">
              Automated package label screening and declaration verification platform.
            </p>
          </div>

          <div className="footer-nav-block">
            <span className="footer-nav-heading">Navigation</span>
            <button type="button" className="footer-link" onClick={() => scrollToSection('inspection-workspace')}>
              Inspect
            </button>
            <button type="button" className="footer-link" onClick={() => scrollToSection('how-it-works')}>
              How it works
            </button>
            <button type="button" className="footer-link" onClick={() => scrollToSection('about')}>
              About
            </button>
          </div>
        </div>

        <div className="footer-bottom-row">
          <p className="footer-disclaimer">
            LegalCheck is an AI-assisted screening tool. Results are intended for advisory review and require verification by qualified personnel before enforcement or legal determination.
          </p>
          <span className="footer-meta-tiny">SIH 2026 · Problem ID SIH26034</span>
        </div>
      </div>
    </footer>
  );
};
