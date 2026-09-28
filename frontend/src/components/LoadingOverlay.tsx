import React from 'react';

export const LoadingOverlay: React.FC = () => {
  return (
    <div className="workspace-loading-card">
      <div className="loading-spinner-wrapper">
        <span className="loading-ring"></span>
      </div>
      <h3 className="loading-headline">Analyzing package declarations</h3>
      <p className="loading-subtext">Extracting label information and checking configured requirements...</p>
    </div>
  );
};
