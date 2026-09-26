import React from 'react';

export const HowItWorks: React.FC = () => {
  return (
    <section id="how-it-works" className="how-it-works-section">
      <div className="section-container">
        <div className="section-header">
          <h2 className="section-title">How LegalCheck works</h2>
          <p className="section-subtitle">A simple, structured approach to package label screening</p>
        </div>

        <div className="steps-grid">
          <div className="step-card">
            <span className="step-number">01</span>
            <h3 className="step-title">Capture</h3>
            <p className="step-desc">
              Upload a package image or capture a clear photo of the product label using your device camera.
            </p>
          </div>

          <div className="step-card">
            <span className="step-number">02</span>
            <h3 className="step-title">Analyze</h3>
            <p className="step-desc">
              Extracted text is processed to detect key declarations such as Net Quantity, MRP, Manufacturer, and Dates.
            </p>
          </div>

          <div className="step-card">
            <span className="step-number">03</span>
            <h3 className="step-title">Review</h3>
            <p className="step-desc">
              Receive a structured audit report highlighting detected values, missing items, and verification notes.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};
