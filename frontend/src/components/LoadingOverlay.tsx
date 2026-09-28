import React, { useState, useEffect } from 'react';

const PROCESSING_STEPS = [
  { label: 'Uploading Images', icon: '📤' },
  { label: 'Preprocessing', icon: '🔍' },
  { label: 'Extracting Text', icon: '📄' },
  { label: 'AI Interpretation', icon: '🤖' },
  { label: 'Classifying Product', icon: '🏷️' },
  { label: 'Checking Rules', icon: '⚖️' },
  { label: 'Generating Report', icon: '📊' },
];

export const LoadingOverlay: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    // Step transition timer (~400ms per step for fast response)
    const interval = setInterval(() => {
      setCurrentStep((prev) => {
        if (prev < PROCESSING_STEPS.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 450);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="workspace-loading-card">
      <div className="loading-spinner-wrapper">
        <span className="loading-ring"></span>
      </div>
      <h3 className="loading-headline">Processing Inspection</h3>
      <p className="loading-subtext">OpenCV Preprocessing & Gemini Text-Only Pipeline</p>

      {/* Step Sequence Indicator */}
      <div className="loading-steps-container" style={{ marginTop: '1.25rem', width: '100%', maxWidth: '420px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', textAlign: 'left' }}>
          {PROCESSING_STEPS.map((step, idx) => {
            const isCompleted = idx < currentStep;
            const isCurrent = idx === currentStep;
            return (
              <div
                key={step.label}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  fontSize: '0.85rem',
                  fontWeight: isCurrent ? 600 : 400,
                  color: isCurrent ? 'var(--color-accent-blue, #2563eb)' : isCompleted ? '#10b981' : '#9ca3af',
                  transition: 'all 0.2s ease'
                }}
              >
                <span style={{ fontSize: '1rem', width: '20px', textAlign: 'center' }}>
                  {isCompleted ? '✓' : step.icon}
                </span>
                <span>{step.label}</span>
                {isCurrent && <span className="btn-spinner" style={{ width: '12px', height: '12px', marginLeft: 'auto' }}></span>}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
