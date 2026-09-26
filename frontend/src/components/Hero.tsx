import React from 'react';

interface HeroProps {
  onStartInspectionClick: () => void;
}

export const Hero: React.FC<HeroProps> = ({ onStartInspectionClick }) => {
  const scrollToInspection = () => {
    onStartInspectionClick();
    const el = document.getElementById('inspection-workspace');
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <section className="hero-root">
      <div className="hero-container hero-centered">
        <div className="hero-text-block">
          <span className="hero-eyebrow">Automated Commodity Screening</span>
          <h1 className="hero-heading">Inspect package labels with confidence.</h1>
          <p className="hero-subheading">
            Upload or capture one or more package photos to verify mandatory legal metrology declarations, 
            detect missing details, and generate compliance reports.
          </p>

          <div className="hero-actions">
            <button type="button" className="btn-hero-primary" onClick={scrollToInspection}>
              Start package inspection
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>
            </button>
            <a href="#how-it-works" className="btn-hero-secondary">
              How screening works
            </a>
          </div>
        </div>
      </div>
    </section>
  );
};
