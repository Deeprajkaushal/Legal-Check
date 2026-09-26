import React, { useState, useRef } from 'react';
import type { SelectedImage } from '../types';

interface InspectionAreaProps {
  images: SelectedImage[];
  onAddFiles: (files: File[]) => void;
  onRemoveImage: (id: string) => void;
  onClearAllImages: () => void;
  onOpenCamera: () => void;
  onInspect: () => void;
  onInspectUrl: (url: string) => void;
  loading: boolean;
  inspectingIndex: number;
  cameraOpen: boolean;
}

export const InspectionArea: React.FC<InspectionAreaProps> = ({
  images,
  onAddFiles,
  onRemoveImage,
  onClearAllImages,
  onOpenCamera,
  onInspect,
  onInspectUrl,
  loading,
  inspectingIndex,
  cameraOpen,
}) => {
  const [inspectionMode, setInspectionMode] = useState<'package' | 'url'>('package');
  const [urlInput, setUrlInput] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const validFiles: File[] = [];
      for (let i = 0; i < e.dataTransfer.files.length; i++) {
        const file = e.dataTransfer.files[i];
        if (file.type.startsWith('image/')) {
          validFiles.push(file);
        }
      }
      if (validFiles.length > 0) {
        onAddFiles(validFiles);
      }
    }
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const validFiles: File[] = Array.from(e.target.files).filter((f) =>
        f.type.startsWith('image/')
      );
      if (validFiles.length > 0) {
        onAddFiles(validFiles);
      }
    }
    // Reset file input value
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const totalImages = images.length;

  return (
    <section id="inspection-workspace" className="workspace-section">
      <div className="workspace-header">
        <h2 className="workspace-title">
          {inspectionMode === 'url'
            ? 'Digital Product Inspection'
            : images.length > 0
            ? 'Review package photos'
            : 'Upload package images'}
        </h2>
        <p className="workspace-subtitle">
          {inspectionMode === 'url'
            ? 'Inspect publicly available product information from an e-commerce or manufacturer webpage.'
            : 'Add one or multiple photos of the commodity label (Front, Back, Side) for screening.'}
        </p>

        {/* Mode Selector Tabs */}
        <div className="inspection-mode-tabs-wrapper">
          <div className="inspection-mode-tabs">
            <button
              type="button"
              className={`btn-mode-tab ${inspectionMode === 'package' ? 'active' : ''}`}
              onClick={() => setInspectionMode('package')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                <circle cx="8.5" cy="8.5" r="1.5" />
                <polyline points="21 15 16 10 5 21" />
              </svg>
              Package Scan
            </button>

            <button
              type="button"
              className={`btn-mode-tab ${inspectionMode === 'url' ? 'active' : ''}`}
              onClick={() => setInspectionMode('url')}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="2" y1="12" x2="22" y2="12" />
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
              </svg>
              Digital Inspection
            </button>
          </div>
        </div>
      </div>

      <div className="workspace-card">
        {/* Digital Inspection URL View */}
        {inspectionMode === 'url' ? (
          <div className="url-inspect-container">
            <div className="url-inspect-header">
              <div className="url-badge-tag">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="2" y1="12" x2="22" y2="12" />
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                </svg>
                Digital Inspection Mode
              </div>
              <h3 className="url-title">Enter a public product page URL</h3>
              <p className="url-subtitle">
                Paste the full web address of an e-commerce or manufacturer product page to screen visible legal declarations.
              </p>
            </div>

            <form
              className="url-input-form"
              onSubmit={(e) => {
                e.preventDefault();
                if (urlInput.trim()) {
                  onInspectUrl(urlInput.trim());
                }
              }}
            >
              <div className="url-input-group">
                <div className="url-input-field-wrapper">
                  <div className="url-icon-prefix">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="2" y1="12" x2="22" y2="12" />
                      <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                    </svg>
                  </div>

                  <input
                    type="url"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    placeholder="https://example.com/product/abc"
                    className="url-input"
                    required
                    disabled={loading}
                  />
                </div>

                <button
                  type="submit"
                  className="btn-inspect-primary btn-url-submit"
                  disabled={loading || !urlInput.trim()}
                >
                  {loading ? (
                    <>
                      <span className="btn-spinner"></span>
                      Inspecting URL...
                    </>
                  ) : (
                    <>
                      Inspect URL
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="5" y1="12" x2="19" y2="12" />
                        <polyline points="12 5 19 12 12 19" />
                      </svg>
                    </>
                  )}
                </button>
              </div>

              {/* Quick Sample Buttons */}
              <div className="url-presets-wrapper">
                <span className="url-presets-label">Quick Try Sample URLs:</span>
                <div className="url-presets-list">
                  <button
                    type="button"
                    className="btn-url-preset"
                    onClick={() => setUrlInput('https://amul.com/products/amul-taaza-toned-milk.php')}
                    disabled={loading}
                  >
                    🥛 Amul Taaza Milk
                  </button>
                  <button
                    type="button"
                    className="btn-url-preset"
                    onClick={() => setUrlInput('https://www.parleproducts.com/brands/parle-g')}
                    disabled={loading}
                  >
                    🍪 Parle-G Biscuits
                  </button>
                  <button
                    type="button"
                    className="btn-url-preset"
                    onClick={() => setUrlInput('https://example.com/product/sample-imported-commodity')}
                    disabled={loading}
                  >
                    🍫 Sample Product URL
                  </button>
                </div>
              </div>

              <p className="url-disclaimer-hint">
                * Note: Digital product-page screening evaluates publicly available web declarations under Legal Metrology Rules, 2011. Physical package verification may be required.
              </p>
            </form>
          </div>
        ) : (
          <>
            {/* Strictly hidden multi-file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden-file-input"
              onChange={handleFileInputChange}
              style={{ display: 'none', width: 0, height: 0, opacity: 0, position: 'absolute' }}
            />

        {images.length > 0 ? (
          <div className="multi-image-workspace">
            {/* Top Toolbar */}
            <div className="workspace-bar">
              <div className="bar-left">
                <span className="images-ready-count">
                  <strong>{images.length}</strong> photo{images.length > 1 ? 's' : ''} ready
                </span>
                <span className="bar-hint">Front, back, side labels</span>
              </div>

              <div className="bar-actions">
                <button
                  type="button"
                  className="btn-text-sm text-danger"
                  onClick={onClearAllImages}
                  disabled={loading}
                >
                  Clear all
                </button>
              </div>
            </div>

            {/* Thumbnail Grid */}
            <div className="thumbnails-grid">
              {images.map((img, idx) => (
                <div key={img.id} className="thumb-card">
                  <div className="thumb-image-container">
                    <img src={img.previewUrl} alt={`Package photo ${idx + 1}`} className="thumb-img" />
                    <span className="thumb-number-badge">Image {idx + 1}</span>
                    <button
                      type="button"
                      className="thumb-remove-btn"
                      onClick={() => onRemoveImage(img.id)}
                      disabled={loading}
                      aria-label={`Remove image ${idx + 1}`}
                      title="Remove image"
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </div>
                  <div className="thumb-info-bar">
                    <span className="thumb-filename" title={img.file.name}>{img.file.name}</span>
                    <span className="thumb-filesize">{formatFileSize(img.file.size)}</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Side-by-Side Add More Buttons */}
            <div className="upload-actions-equal-grid">
              <button
                type="button"
                className="btn-workspace-action secondary"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <div className="btn-action-text-group">
                  <span className="btn-action-title">Select more images</span>
                  <span className="btn-action-sub">Browse from device</span>
                </div>
              </button>

              <button
                type="button"
                className="btn-workspace-action secondary"
                onClick={onOpenCamera}
                disabled={cameraOpen || loading}
              >
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                  <circle cx="12" cy="13" r="4" />
                </svg>
                <div className="btn-action-text-group">
                  <span className="btn-action-title">Take photo</span>
                  <span className="btn-action-sub">Snap with camera</span>
                </div>
              </button>
            </div>

            {/* Inspection Trigger & Progress */}
            <div className="inspect-action-footer">
              {loading ? (
                <div className="inspection-progress-block">
                  <div className="progress-text-row">
                    <span className="btn-spinner"></span>
                    <span className="progress-status-text">
                      Inspecting image {Math.min(inspectingIndex + 1, totalImages)} of {totalImages}...
                    </span>
                  </div>
                  <div className="progress-bar-track">
                    <div
                      className="progress-bar-fill"
                      style={{
                        width: `${Math.round(((inspectingIndex + 1) / totalImages) * 100)}%`,
                      }}
                    />
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  className="btn-inspect-primary"
                  onClick={onInspect}
                  disabled={images.length === 0}
                >
                  Inspect package
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="5" y1="12" x2="19" y2="12" />
                    <polyline points="12 5 19 12 12 19" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        ) : (
          <div className="upload-drop-zone-container">
            <div
              className={`upload-drop-zone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
            >
              <div className="upload-icon-circle">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
              </div>

              <div className="upload-text-group">
                <span className="upload-main-text">Drag & drop package images here</span>
                <span className="upload-sub-text">Select one or multiple photos (Front, Back, Label side) · JPG, PNG, WEBP</span>
              </div>
            </div>

            {/* Prominent Side-by-Side Equal Action Buttons */}
            <div className="upload-actions-equal-grid">
              <button
                type="button"
                className="btn-workspace-action"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
              >
                <div className="action-icon-wrapper">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <circle cx="8.5" cy="8.5" r="1.5" />
                    <polyline points="21 15 16 10 5 21" />
                  </svg>
                </div>
                <div className="btn-action-text-group">
                  <span className="btn-action-title">Select images</span>
                  <span className="btn-action-sub">Browse from device</span>
                </div>
              </button>

              <button
                type="button"
                className="btn-workspace-action"
                onClick={onOpenCamera}
                disabled={cameraOpen || loading}
              >
                <div className="action-icon-wrapper">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
                    <circle cx="12" cy="13" r="4" />
                  </svg>
                </div>
                <div className="btn-action-text-group">
                  <span className="btn-action-title">Take photo</span>
                  <span className="btn-action-sub">Use live camera</span>
                </div>
              </button>
            </div>
          </div>
        )}
        </>
        )}
      </div>
    </section>
  );
};
