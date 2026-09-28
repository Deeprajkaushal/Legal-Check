import React, { useEffect, useState } from 'react';

const PIPELINE_STEPS = [
  { id: 'upload', label: 'Uploading Images', desc: 'Receiving package image file(s)' },
  { id: 'preprocess', label: 'Preprocessing', desc: 'Applying OpenCV contrast & sharpening' },
  { id: 'ocr', label: 'Extracting Text', desc: 'Running local OCR engine' },
  { id: 'ai', label: 'AI Interpretation', desc: 'Sending extracted text to Gemini (Text-Only)' },
  { id: 'classify', label: 'Classifying Product', desc: 'Determining commodity category & package type' },
  { id: 'rules', label: 'Checking Rules', desc: 'Running deterministic Legal Metrology rules engine' },
  { id: 'report', label: 'Generating Report', desc: 'Building explainable inspection summary' },
];

export const LoadingOverlay: React.FC = () => {
  const [activeStepIdx, setActiveStepIdx] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setActiveStepIdx((prev) => (prev < PIPELINE_STEPS.length - 1 ? prev + 1 : prev));
    }, 700);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="workspace-loading-card">
      <div className="loading-spinner-wrapper">
        <span className="loading-ring"></span>
      </div>
      <h3 className="loading-headline">Processing Legal Metrology Inspection</h3>
      <p className="loading-subtext">Executing OCR + OpenCV pipeline and rule verification</p>

      {/* Stepper Pipeline UI */}
      <div className="pipeline-stepper-wrapper">
        <div className="pipeline-steps-list">
          {PIPELINE_STEPS.map((step, idx) => {
            const isCompleted = idx < activeStepIdx;
            const isCurrent = idx === activeStepIdx;
            return (
              <div
                key={step.id}
                className={`pipeline-step-item ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}`}
              >
                <div className="step-indicator">
                  {isCompleted ? (
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  ) : (
                    <span>{idx + 1}</span>
                  )}
                </div>
                <div className="step-content">
                  <span className="step-label">{step.label}</span>
                  {isCurrent && <span className="step-desc">{step.desc}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
