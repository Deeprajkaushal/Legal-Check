import { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Hero } from './components/Hero';
import { InspectionArea } from './components/InspectionArea';
import { CameraModal } from './components/CameraModal';
import { LoadingOverlay } from './components/LoadingOverlay';
import { ErrorBanner } from './components/ErrorBanner';
import { ResultsDashboard } from './components/ResultsDashboard';
import { HistorySection } from './components/HistorySection';
import { HowItWorks } from './components/HowItWorks';
import { AboutSection } from './components/AboutSection';
import { Footer } from './components/Footer';
import type { InspectionResponse, AppState, ActiveTab, SelectedImage, HistoryItem } from './types';
import { getHistory, saveToHistory, clearHistory, createThumbnail } from './utils/history';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'https://legalcheck-backend.onrender.com';

export function App() {
  const [images, setImages] = useState<SelectedImage[]>([]);
  const [result, setResult] = useState<InspectionResponse | null>(null);
  const [appState, setAppState] = useState<AppState>('initial');
  const [activeTab, setActiveTab] = useState<ActiveTab>('inspect');
  const [inspectingIndex, setInspectingIndex] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);

  // Load history from localStorage on initial render
  useEffect(() => {
    setHistoryItems(getHistory());
  }, []);

  // Clean up object URLs when images state changes or unmounts
  useEffect(() => {
    return () => {
      images.forEach((img) => URL.revokeObjectURL(img.previewUrl));
    };
  }, [images]);

  const handleAddFiles = (newFiles: File[]) => {
    const valid = newFiles.filter((f) => f.type.startsWith('image/'));
    if (valid.length === 0) {
      setErrorMsg('Please select valid image files (JPG, PNG, WEBP).');
      setAppState('error');
      return;
    }

    const newSelected: SelectedImage[] = valid.map((file) => ({
      id: `img-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
      file,
      previewUrl: URL.createObjectURL(file),
    }));

    setImages((prev) => [...prev, ...newSelected]);
    setResult(null);
    setErrorMsg('');
    setAppState('image_ready');
    setActiveTab('inspect');
  };

  const handleRemoveImage = (id: string) => {
    setImages((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target) {
        URL.revokeObjectURL(target.previewUrl);
      }
      const updated = prev.filter((item) => item.id !== id);
      if (updated.length === 0) {
        setAppState('initial');
      }
      return updated;
    });
  };

  const handleClearAllImages = () => {
    images.forEach((img) => URL.revokeObjectURL(img.previewUrl));
    setImages([]);
    setResult(null);
    setErrorMsg('');
    setAppState('initial');
  };

  const handleCameraCapture = (file: File) => {
    handleAddFiles([file]);
    setAppState('image_ready');
  };

  const inspectPackage = async () => {
    if (images.length === 0) {
      setErrorMsg('Please select or capture at least one package image first.');
      setAppState('error');
      return;
    }

    setAppState('inspecting');
    setInspectingIndex(0);
    setErrorMsg('');

    try {
      const formData = new FormData();
      images.forEach((img, i) => {
        const imageFile = img.file.type
          ? img.file
          : new File([img.file], img.file.name || `package-${i + 1}.jpg`, { type: 'image/jpeg' });
        formData.append('images', imageFile, imageFile.name);
      });

      const response = await fetch(`${API_URL}/inspect`, {
        method: 'POST',
        body: formData,
      });

      const rawText = await response.text();
      let data: Record<string, unknown> = {};
      if (rawText) {
        try {
          data = JSON.parse(rawText);
        } catch {
          data = { detail: rawText };
        }
      }

      if (!response.ok) {
        let detail =
          typeof data.detail === 'string'
            ? data.detail
            : (data.message as string) || `Server returned HTTP ${response.status}.`;
        if (detail.includes('429') || detail.includes('RESOURCE_EXHAUSTED')) {
          detail = 'Gemini AI rate limit temporarily reached. Please wait 15-30 seconds and try again.';
        }
        throw new Error(detail);
      }

      const combinedResult = data as unknown as InspectionResponse;
      setResult(combinedResult);
      setAppState('success');

      // Create thumbnail for history
      let thumbUrl = '';
      try {
        thumbUrl = await createThumbnail(images[0].file);
      } catch (thumbErr) {
        console.warn('Failed to generate history thumbnail:', thumbErr);
      }

      // Save to localStorage history (max 5 items)
      const updatedHistory = saveToHistory(combinedResult, thumbUrl);
      setHistoryItems(updatedHistory);
    } catch (err) {
      console.error('Inspection API Error:', err);
      let message =
        err instanceof Error
          ? err.message
          : 'Could not connect to the inspection backend server.';

      if (message === 'Failed to fetch') {
        message = `Could not connect to backend server at ${API_URL}. Please ensure the backend server is running.`;
      }

      setErrorMsg(message);
      setAppState('error');
    }
  };

  const inspectUrl = async (url: string) => {
    setAppState('inspecting');
    setErrorMsg('');

    try {
      const response = await fetch(`${API_URL}/inspect-url`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      const rawText = await response.text();
      let data: Record<string, unknown> = {};
      if (rawText) {
        try {
          data = JSON.parse(rawText);
        } catch {
          data = { detail: rawText };
        }
      }

      if (!response.ok) {
        let detail =
          typeof data.detail === 'string'
            ? data.detail
            : (data.message as string) || `Server returned HTTP ${response.status}.`;
        if (detail.includes('429') || detail.includes('RESOURCE_EXHAUSTED')) {
          detail = 'Gemini AI rate limit temporarily reached. Please wait 15-30 seconds and try again.';
        }
        throw new Error(detail);
      }

      const inspectRes = data as unknown as InspectionResponse;
      inspectRes.inspection_type = 'digital';

      setResult(inspectRes);
      setAppState('success');

      // Save to localStorage history
      const updatedHistory = saveToHistory(inspectRes);
      setHistoryItems(updatedHistory);
    } catch (err) {
      console.error('URL Inspection API Error:', err);
      let message =
        err instanceof Error
          ? err.message
          : 'Could not connect to the inspection backend server.';

      if (message === 'Failed to fetch') {
        message = `Could not connect to backend server at ${API_URL}. Please ensure the backend server is running.`;
      }

      setErrorMsg(message);
      setAppState('error');
    }
  };

  const handleReset = () => {
    handleClearAllImages();
    setActiveTab('inspect');
  };

  const handleSelectHistoryItem = (item: HistoryItem) => {
    setResult(item.result);
    setAppState('success');
    setActiveTab('inspect');
  };

  const handleClearHistory = () => {
    clearHistory();
    setHistoryItems([]);
  };

  return (
    <div className="app-root">
      <Header
        activeTab={activeTab}
        onTabChange={setActiveTab}
        onNewInspection={handleReset}
        historyCount={historyItems.length}
      />

      <main className="main-content">
        {/* View when activeTab === 'inspect' */}
        {activeTab === 'inspect' && (
          <>
            {/* Show Hero only if no images loaded and no active inspection result */}
            {appState === 'initial' && <Hero onStartInspectionClick={() => setActiveTab('inspect')} />}

            {/* Core Inspection Workspace (Upload, Camera & Thumbnails) */}
            {appState !== 'success' && (
              <InspectionArea
                images={images}
                onAddFiles={handleAddFiles}
                onRemoveImage={handleRemoveImage}
                onClearAllImages={handleClearAllImages}
                onOpenCamera={() => setAppState('camera_open')}
                onInspect={inspectPackage}
                onInspectUrl={inspectUrl}
                loading={appState === 'inspecting'}
                inspectingIndex={inspectingIndex}
                cameraOpen={appState === 'camera_open'}
              />
            )}

            {/* Live Camera Viewfinder Modal */}
            {appState === 'camera_open' && (
              <CameraModal
                onCapture={handleCameraCapture}
                onClose={() => setAppState(images.length > 0 ? 'image_ready' : 'initial')}
              />
            )}

            {/* Loading Overlay */}
            {appState === 'inspecting' && <LoadingOverlay />}

            {/* Error Banner */}
            {appState === 'error' && (
              <ErrorBanner message={errorMsg} onRetry={inspectPackage} onReset={handleReset} />
            )}

            {/* Results Workspace */}
            {appState === 'success' && result && (
              <ResultsDashboard result={result} onNewInspection={handleReset} />
            )}
          </>
        )}

        {/* View when activeTab === 'history' */}
        {activeTab === 'history' && (
          <HistorySection
            historyItems={historyItems}
            onSelectHistoryItem={handleSelectHistoryItem}
            onClearHistory={handleClearHistory}
            onStartNewInspection={handleReset}
          />
        )}

        {/* View when activeTab === 'about' or always present at bottom */}
        {(activeTab === 'about' || activeTab === 'inspect') && (
          <>
            <HowItWorks />
            <AboutSection />
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}

export default App;
