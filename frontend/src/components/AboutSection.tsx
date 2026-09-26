import React from 'react';

export const AboutSection: React.FC = () => {
  return (
    <section id="about" className="about-section">
      <div className="section-container">
        <div className="about-card">
          <div className="about-text-content">
            <span className="about-eyebrow">Product Philosophy</span>
            <h2 className="about-title">Built for clearer package inspections.</h2>
            <p className="about-body">
              LegalCheck was developed to simplify commodity inspection workflows. By combining 
              automated label extraction with deterministic rule engines, it provides quick visibility 
              into package declarations and highlights potential compliance gaps.
            </p>
            <p className="about-body-secondary">
              Evaluations are checked against standard requirements under the 
              Legal Metrology (Packaged Commodities) Rules, 2011 to support pre-audit screenings 
              and verification reviews.
            </p>
          </div>

          <div className="about-stats-column">
            <div className="stat-box">
              <span className="stat-label">Analysis Speed</span>
              <strong className="stat-value">Seconds</strong>
            </div>
            <div className="stat-box">
              <span className="stat-label">Rule Execution</span>
              <strong className="stat-value">Deterministic</strong>
            </div>
            <div className="stat-box">
              <span className="stat-label">Human Review</span>
              <strong className="stat-value">Required</strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
