import React, { useEffect, useRef, useState } from 'react';

interface CameraModalProps {
  onCapture: (file: File) => void;
  onClose: () => void;
}

export const CameraModal: React.FC<CameraModalProps> = ({ onCapture, onClose }) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [error, setError] = useState<string>('');
  const [facingMode, setFacingMode] = useState<'environment' | 'user'>('environment');
  const [isInitializing, setIsInitializing] = useState<boolean>(true);
  const [retryTrigger, setRetryTrigger] = useState<number>(0);

  useEffect(() => {
    let active = true;

    const initCamera = async () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        if (active) {
          setError('Camera access is not supported by this browser context (HTTPS or localhost required).');
          setIsInitializing(false);
        }
        return;
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: facingMode },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
          audio: false,
        });

        if (!active) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }

        streamRef.current = stream;

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play().catch((err) => {
            console.warn('Video play error:', err);
          });
        }

        if (active) {
          setError('');
          setIsInitializing(false);
        }
      } catch (err) {
        console.error('Camera access error:', err);
        if (active) {
          setError('Camera permission was denied or the camera is unavailable.');
          setIsInitializing(false);
        }
      }
    };

    void initCamera();

    return () => {
      active = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
      }
    };
  }, [facingMode, retryTrigger]);

  const toggleCamera = () => {
    setIsInitializing(true);
    setError('');
    setFacingMode((prev) => (prev === 'environment' ? 'user' : 'environment'));
  };

  const handleRetry = () => {
    setIsInitializing(true);
    setError('');
    setRetryTrigger((prev) => prev + 1);
  };

  const handleCapture = () => {
    const video = videoRef.current;
    if (!video || video.videoWidth === 0) {
      setError('Camera is not ready yet.');
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      setError('Failed to capture frame from camera.');
      return;
    }

    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setError('Failed to encode captured photo.');
          return;
        }

        const capturedFile = new File([blob], `camera-capture-${Date.now()}.jpg`, {
          type: 'image/jpeg',
        });

        onCapture(capturedFile);
      },
      'image/jpeg',
      0.95
    );
  };

  return (
    <div className="camera-modal-backdrop">
      <div className="camera-modal-card">
        <div className="camera-modal-header">
          <div>
            <h3 className="camera-modal-title">Take package photo</h3>
            <p className="camera-modal-subtitle">Center the commodity label in frame</p>
          </div>
          <button type="button" className="close-modal-btn" onClick={onClose} aria-label="Close camera">
            ✕
          </button>
        </div>

        <div className="camera-viewfinder-container">
          {isInitializing && (
            <div className="camera-state-box">
              <span className="btn-spinner lg"></span>
              <p>Initializing camera...</p>
            </div>
          )}

          {error ? (
            <div className="camera-state-box text-danger">
              <p>{error}</p>
              <button type="button" className="btn-secondary-sm" onClick={handleRetry}>
                Try again
              </button>
            </div>
          ) : (
            <video ref={videoRef} autoPlay playsInline muted className="camera-video-feed" />
          )}

          {!error && !isInitializing && (
            <div className="viewfinder-overlay">
              <div className="target-frame-box">
                <span className="target-guide-text">Align label here</span>
              </div>
            </div>
          )}
        </div>

        <div className="camera-modal-footer">
          <button
            type="button"
            className="btn-modal-secondary"
            onClick={toggleCamera}
            disabled={isInitializing || !!error}
          >
            Switch to {facingMode === 'environment' ? 'Front' : 'Rear'} camera
          </button>

          <button
            type="button"
            className="btn-modal-primary"
            onClick={handleCapture}
            disabled={isInitializing || !!error}
          >
            Capture photo
          </button>
        </div>
      </div>
    </div>
  );
};
