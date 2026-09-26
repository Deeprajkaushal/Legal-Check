import type { HistoryItem, InspectionResponse } from '../types';

const HISTORY_KEY = 'legalcheck_scan_history';
const MAX_HISTORY_ITEMS = 5;

export const getHistory = (): HistoryItem[] => {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) {
      return parsed;
    }
    return [];
  } catch (err) {
    console.error('Failed to parse history from localStorage:', err);
    return [];
  }
};

export const saveToHistory = (
  result: InspectionResponse,
  thumbnailUrl?: string
): HistoryItem[] => {
  try {
    const existing = getHistory();
    const now = new Date();
    
    // Format timestamp human friendly (e.g. "Today, 10:42 AM" or date string)
    const formattedDate = new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    }).format(now);

    const newItem: HistoryItem = {
      id: result.inspection_id || `scan-${Date.now()}`,
      timestamp: now.toISOString(),
      formattedDate,
      productName: result.product.name || result.declarations.product_name || 'Unidentified Package',
      category: result.product.category || 'General Commodity',
      status: result.compliance.status,
      violationsCount: result.compliance.violations?.length || 0,
      thumbnailUrl: thumbnailUrl || undefined,
      result,
    };

    // Filter out duplicates if same inspection_id exists
    const filtered = existing.filter((item) => item.id !== newItem.id);

    // Prepend new item, keep max 5 items
    const updated = [newItem, ...filtered].slice(0, MAX_HISTORY_ITEMS);

    localStorage.setItem(HISTORY_KEY, JSON.stringify(updated));
    return updated;
  } catch (err) {
    console.error('Failed to save inspection to localStorage history:', err);
    return getHistory();
  }
};

export const clearHistory = (): void => {
  try {
    localStorage.removeItem(HISTORY_KEY);
  } catch (err) {
    console.error('Failed to clear history:', err);
  }
};

/**
 * Creates a small compressed base64 data URL from a File object for thumbnail display in history.
 */
export const createThumbnail = (file: File): Promise<string> => {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const maxDim = 120;
        let width = img.width;
        let height = img.height;

        if (width > height) {
          if (width > maxDim) {
            height = Math.round((height * maxDim) / width);
            width = maxDim;
          }
        } else {
          if (height > maxDim) {
            width = Math.round((width * maxDim) / height);
            height = maxDim;
          }
        }

        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height);
          resolve(canvas.toDataURL('image/jpeg', 0.7));
        } else {
          resolve('');
        }
      };
      img.onerror = () => resolve('');
      img.src = e.target?.result as string;
    };
    reader.onerror = () => resolve('');
    reader.readAsDataURL(file);
  });
};
