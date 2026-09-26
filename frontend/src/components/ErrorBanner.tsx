import React from 'react';

interface ErrorBannerProps {
  message: string;
  onRetry: () => void;
  onReset: () => void;
}

export const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onRetry, onReset }) => {
  return (
    <div className="workspace-error-card">
      <div className="error-card-content">
        <div className="error-title-row">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
          <h3 className="error-headline">Inspection could not be completed</h3>
        </div>
        <p className="error-message-text">{message}</p>
        <span className="error-tip">
          Make sure your server endpoint is active at <code>http://127.0.0.1:8000</code> and the image file is clear.
        </span>

        <div className="error-actions-group">
          <button type="button" className="btn-error-primary" onClick={onRetry}>
            Try again
          </button>
          <button type="button" className="btn-error-secondary" onClick={onReset}>
            Choose another image
          </button>
        </div>
      </div>
    </div>
  );
};
