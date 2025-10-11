import { AnalysisResult, Platform } from '../types';

const API_BASE_URL = 'http://localhost:8000';

export async function analyzeImage(
  file: File,
  platform: Platform
): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('platform', platform);

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || error.error || 'Failed to analyze image');
  }

  return response.json();
}
