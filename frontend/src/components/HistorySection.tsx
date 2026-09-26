import React from 'react';
import type { HistoryItem } from '../types';

interface HistorySectionProps {
  historyItems: HistoryItem[];
  onSelectHistoryItem: (item: HistoryItem) => void;
  onClearHistory: () => void;
  onStartNewInspection: () => void;
}

export const HistorySection: React.FC<HistorySectionProps> = ({
  historyItems,
  onSelectHistoryItem,
  onClearHistory,
  onStartNewInspection,
}) => {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'no_detected_violation':
        return {
          label: 'No detected violation',
          className: 'history-badge-pass',
        };
      case 'requires_human_verification':
        return {
          label: 'Review required',
          className: 'history-badge-warning',
        };
      default:
        return {
          label: 'Potential issue detected',
          className: 'history-badge-issue',
        };
    }
  };

  return (
    <section id="history-section" className="workspace-section">
      <div className="workspace-header history-header-row">
        <div>
          <h2 className="workspace-title">Recent Inspection History</h2>
          <p className="workspace-subtitle">
            Saved locally in your browser. Shows up to the 5 most recent package screenings.
          </p>
        </div>
        {historyItems.length > 0 && (
          <button
            type="button"
            className="btn-text text-muted"
            onClick={onClearHistory}
            title="Clear all saved history"
          >
            Clear history
          </button>
        )}
      </div>

      {historyItems.length === 0 ? (
        <div className="history-empty-state">
          <div className="empty-icon-circle">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <h3 className="empty-title">Your previous inspections will appear here.</h3>
          <p className="empty-subtext">
            Upload package images to perform an inspection. Results will automatically save here for quick reference.
          </p>
          <button type="button" className="btn-hero-primary" onClick={onStartNewInspection}>
            Start first inspection
          </button>
        </div>
      ) : (
        <div className="history-cards-list">
          {historyItems.map((item) => {
            const badge = getStatusBadge(item.status);
            return (
              <div
                key={item.id}
                className="history-card-item"
                onClick={() => onSelectHistoryItem(item)}
              >
                <div className="history-card-thumb">
                  {item.thumbnailUrl ? (
                    <img src={item.thumbnailUrl} alt={item.productName} className="history-thumb-img" />
                  ) : (
                    <div className="history-thumb-placeholder">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
                      </svg>
                    </div>
                  )}
                </div>

                <div className="history-card-body">
                  <div className="history-body-top">
                    <h4 className="history-product-name">{item.productName}</h4>
                    <span className="history-time-stamp">{item.formattedDate}</span>
                  </div>

                  <div className="history-body-bottom">
                    <span className="history-category-pill">{item.category}</span>

                    <div className="history-status-group">
                      <span className={`history-status-pill ${badge.className}`}>
                        {badge.label}
                      </span>
                      {item.violationsCount > 0 && (
                        <span className="history-issues-count">
                          {item.violationsCount} issue{item.violationsCount > 1 ? 's' : ''}
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                <div className="history-card-action">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="9 18 15 12 9 6" />
                  </svg>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
};
