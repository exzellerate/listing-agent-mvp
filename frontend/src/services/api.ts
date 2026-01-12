import { AnalysisResult, Platform, PricingData, TestBatchResponse, ConfirmAnalysisRequest, ConfirmAnalysisResponse, LearningStats, CreateDraftRequest, DraftListing, DraftListingSummary, ListingsResponse, SyncResponse, CategoryAspectRequest, CategoryAspectResponse, CategoryRecommendation } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Custom error class for API errors
export class APIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: string
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Check if the API is reachable
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000), // 5 second timeout
    });
    return response.ok;
  } catch (error) {
    console.error('Health check failed:', error);
    return false;
  }
}

export async function analyzeImages(
  files: File[],
  platform: Platform,
  userContext?: string
): Promise<AnalysisResult> {
  // Validate inputs
  if (!files || files.length === 0) {
    throw new APIError('No files provided', 400);
  }

  if (files.length > 5) {
    throw new APIError('Maximum 5 images allowed', 400);
  }

  if (!['ebay', 'amazon', 'walmart'].includes(platform)) {
    throw new APIError('Invalid platform selected', 400);
  }

  // Validate all files
  const maxSize = 10 * 1024 * 1024; // 10MB per file
  const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif'];

  for (let i = 0; i < files.length; i++) {
    const file = files[i];

    // Check file size
    if (file.size > maxSize) {
      throw new APIError(
        `Image ${i + 1} size (${(file.size / 1024 / 1024).toFixed(2)}MB) exceeds the 10MB limit`,
        400
      );
    }

    // Check file type
    if (!allowedTypes.includes(file.type)) {
      throw new APIError(
        `Invalid file type for image ${i + 1}: ${file.type}. Allowed types: JPEG, PNG, WebP, GIF`,
        400
      );
    }
  }

  const formData = new FormData();
  files.forEach(file => {
    formData.append('files', file);
  });
  formData.append('platform', platform);

  // DEBUG: Log userContext before appending
  console.log('API: userContext parameter received:', JSON.stringify(userContext));
  console.log('API: userContext type:', typeof userContext);
  console.log('API: userContext truthy?', !!userContext);

  if (userContext) {
    console.log('API: Appending user_context to FormData:', userContext);
    formData.append('user_context', userContext);
  } else {
    console.log('API: NOT appending user_context (value is falsy)');
  }

  try {
    // Timeout for image analysis with web search enabled
    // Using 300s base to allow for long-running analysis operations (proxy has 300s timeout)
    const timeout = 300000 + (files.length - 1) * 30000; // 300s base + 30s per additional image

    const response = await fetch(`${API_BASE_URL}/api/analyze`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(timeout),
    });

    if (!response.ok) {
      let errorMessage = 'Failed to analyze images';
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
        errorDetails = errorData.detail || '';
      } catch (e) {
        // If parsing JSON fails, use status text
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // DEBUG: Log API response
    console.log('🔍 API RESPONSE - Full data:', data);
    console.log('🔍 API RESPONSE - ebay_aspects:', data.ebay_aspects);
    console.log('🔍 API RESPONSE - typeof ebay_aspects:', typeof data.ebay_aspects);
    console.log('🔍 API RESPONSE - ebay_aspects keys:', data.ebay_aspects ? Object.keys(data.ebay_aspects) : 'N/A');

    // Validate response structure
    if (!data.product_name || !data.suggested_title || !data.suggested_description) {
      throw new APIError('Invalid response from server: Missing required fields', 500);
    }

    return data;
  } catch (error) {
    // Handle different error types
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. The image analysis took too long. Please try again.',
        408
      );
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIError('Request was cancelled', 499);
    }

    // Unknown error
    throw new APIError(
      `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

// Legacy single-image function for backward compatibility
export async function analyzeImage(
  file: File,
  platform: Platform
): Promise<AnalysisResult> {
  return analyzeImages([file], platform);
}

export async function researchPricing(
  productName: string,
  category: string | null,
  condition: string,
  platform: Platform
): Promise<PricingData> {
  // Validate inputs
  if (!productName || productName.trim() === '') {
    throw new APIError('Product name is required', 400);
  }

  if (!['ebay', 'amazon', 'walmart'].includes(platform)) {
    throw new APIError('Invalid platform selected', 400);
  }

  const requestData = {
    product_name: productName,
    category: category || null,
    condition: condition || 'Used',
    platform,
  };

  try {
    const response = await fetch(`${API_BASE_URL}/api/research-pricing`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestData),
      signal: AbortSignal.timeout(60000), // 60 second timeout for pricing research
    });

    if (!response.ok) {
      let errorMessage = 'Failed to research pricing';
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
        errorDetails = errorData.detail || '';
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // Validate response structure
    if (!data.statistics || !data.confidence_score) {
      throw new APIError('Invalid pricing data from server', 500);
    }

    return data;
  } catch (error) {
    // Handle different error types
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. Pricing research took too long. Please try again.',
        408
      );
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIError('Request was cancelled', 499);
    }

    // Unknown error
    throw new APIError(
      `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

export async function runBatchTests(csvFile: File): Promise<TestBatchResponse> {
  // Validate input
  if (!csvFile) {
    throw new APIError('No CSV file provided', 400);
  }

  if (!csvFile.name.endsWith('.csv')) {
    throw new APIError('File must be a CSV file', 400);
  }

  const formData = new FormData();
  formData.append('file', csvFile);

  try {
    const response = await fetch(`${API_BASE_URL}/api/test/batch`, {
      method: 'POST',
      body: formData,
      signal: AbortSignal.timeout(600000), // 10 minute timeout for batch tests
    });

    if (!response.ok) {
      let errorMessage = 'Failed to run batch tests';
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
        errorDetails = errorData.detail || '';
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // Validate response structure
    if (!data.summary || !data.results) {
      throw new APIError('Invalid test results from server', 500);
    }

    return data;
  } catch (error) {
    // Handle different error types
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Batch tests timed out. Large test sets may take several minutes.',
        408
      );
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIError('Tests were cancelled', 499);
    }

    // Unknown error
    throw new APIError(
      `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

// Learning System API Functions

export async function confirmAnalysis(
  request: ConfirmAnalysisRequest
): Promise<ConfirmAnalysisResponse> {
  // Validate input
  if (!request.analysis_id) {
    throw new APIError('Analysis ID is required', 400);
  }

  if (!request.user_action) {
    throw new APIError('User action is required', 400);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/analyses/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!response.ok) {
      let errorMessage = 'Failed to confirm analysis';
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
        errorDetails = errorData.detail || '';
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // Validate response structure
    if (!data.success || !data.analysis_id) {
      throw new APIError('Invalid response from server', 500);
    }

    return data;
  } catch (error) {
    // Handle different error types
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. Please try again.',
        408
      );
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIError('Request was cancelled', 499);
    }

    // Unknown error
    throw new APIError(
      `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

export async function getLearningStats(): Promise<LearningStats> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/learning/stats`, {
      method: 'GET',
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!response.ok) {
      let errorMessage = 'Failed to fetch learning statistics';
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
        errorDetails = errorData.detail || '';
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // Validate response structure
    if (typeof data.total_analyses !== 'number' || typeof data.learned_products_count !== 'number') {
      throw new APIError('Invalid stats data from server', 500);
    }

    return data;
  } catch (error) {
    // Handle different error types
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. Please try again.',
        408
      );
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIError('Request was cancelled', 499);
    }

    // Unknown error
    throw new APIError(
      `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}


// ============================================================================
// DRAFT LISTINGS API  
// ============================================================================

export async function createDraft(draft: CreateDraftRequest): Promise<DraftListing> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/drafts`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(draft),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || "Failed to create draft",
        response.status,
        errorData.detail
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    throw new APIError(
      `Failed to create draft: ${error instanceof Error ? error.message : "Unknown error"}`,
      500
    );
  }
}

export async function listDrafts(platform?: Platform): Promise<DraftListingSummary[]> {
  try {
    const url = new URL(`${API_BASE_URL}/api/drafts`);
    if (platform) {
      url.searchParams.append("platform", platform);
    }

    const response = await fetch(url.toString());

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || "Failed to fetch drafts",
        response.status,
        errorData.detail
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    throw new APIError(
      `Failed to fetch drafts: ${error instanceof Error ? error.message : "Unknown error"}`,
      500
    );
  }
}

export async function getDraft(draftId: number): Promise<DraftListing> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/drafts/${draftId}`);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `Draft ${draftId} not found`,
        response.status,
        errorData.detail
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    throw new APIError(
      `Failed to fetch draft: ${error instanceof Error ? error.message : "Unknown error"}`,
      500
    );
  }
}

export async function deleteDraft(draftId: number): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/drafts/${draftId}`, {
      method: "DELETE",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `Failed to delete draft ${draftId}`,
        response.status,
        errorData.detail
      );
    }
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    throw new APIError(
      `Failed to delete draft: ${error instanceof Error ? error.message : "Unknown error"}`,
      500
    );
  }
}


// ============================================================================
// LISTING MANAGEMENT API
// ============================================================================

export async function getActiveListings(page: number = 1, limit: number = 20): Promise<ListingsResponse> {
  try {
    const url = new URL(`${API_BASE_URL}/api/listings/active`);
    url.searchParams.append("page", page.toString());
    url.searchParams.append("limit", limit.toString());

    const response = await fetch(url.toString(), {
      method: "GET",
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || "Failed to fetch active listings",
        response.status,
        errorData.detail
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. Please try again.',
        408
      );
    }

    throw new APIError(
      `Failed to fetch active listings: ${error instanceof Error ? error.message : "Unknown error"}`,
      500
    );
  }
}

export async function getSoldListings(page: number = 1, limit: number = 20): Promise<ListingsResponse> {
  try {
    const url = new URL(`${API_BASE_URL}/api/listings/sold`);
    url.searchParams.append("page", page.toString());
    url.searchParams.append("limit", limit.toString());

    const response = await fetch(url.toString(), {
      method: "GET",
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || "Failed to fetch sold listings",
        response.status,
        errorData.detail
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. Please try again.',
        408
      );
    }

    throw new APIError(
      `Failed to fetch sold listings: ${error instanceof Error ? error.message : "Unknown error"}`,
      500
    );
  }
}

export async function syncListings(): Promise<SyncResponse> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/listings/sync`, {
      method: "POST",
      signal: AbortSignal.timeout(30000), // 30 second timeout for sync operation
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || "Failed to sync listings",
        response.status,
        errorData.detail
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Sync operation timed out. Please try again.',
        408
      );
    }

    throw new APIError(
      `Failed to sync listings: ${error instanceof Error ? error.message : "Unknown error"}`,
      500
    );
  }
}


// ============================================================================
// CATEGORY ASPECT ANALYSIS API
// ============================================================================

export async function analyzeCategoryAspects(
  request: CategoryAspectRequest
): Promise<CategoryAspectResponse> {
  // Validate input
  if (!request.analysis_id) {
    throw new APIError('Analysis ID is required', 400);
  }

  if (!request.category_id) {
    throw new APIError('Category ID is required', 400);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze/category-aspects`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
      signal: AbortSignal.timeout(90000), // 90 second timeout for Claude analysis
    });

    if (!response.ok) {
      let errorMessage = 'Failed to analyze category aspects';
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
        errorDetails = errorData.detail || '';
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // Validate response structure
    if (!data.analysis_id || !data.category_id || !data.aspect_analysis) {
      throw new APIError('Invalid response from server', 500);
    }

    return data;
  } catch (error) {
    // Handle different error types
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. Category aspect analysis took too long. Please try again.',
        408
      );
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIError('Request was cancelled', 499);
    }

    // Unknown error
    throw new APIError(
      `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

// Get category recommendations for a completed analysis
export async function getCategoryRecommendations(
  analysisId: number
): Promise<CategoryRecommendation[]> {
  // Validate input
  if (!analysisId) {
    throw new APIError('Analysis ID is required', 400);
  }

  try {
    const response = await fetch(`${API_BASE_URL}/api/analyze/${analysisId}/categories`, {
      method: 'GET',
      signal: AbortSignal.timeout(30000), // 30 second timeout
    });

    if (!response.ok) {
      let errorMessage = 'Failed to get category recommendations';
      let errorDetails = '';

      try {
        const errorData = await response.json();
        errorMessage = errorData.error || errorData.detail || errorMessage;
        errorDetails = errorData.detail || '';
      } catch (e) {
        errorMessage = response.statusText || errorMessage;
      }

      throw new APIError(errorMessage, response.status, errorDetails);
    }

    const data = await response.json();

    // Return the categories array
    return data.categories || [];
  } catch (error) {
    // Handle different error types
    if (error instanceof APIError) {
      throw error;
    }

    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'Unable to connect to the server. Please ensure the backend is running.',
        0,
        'Network error'
      );
    }

    if (error instanceof DOMException && error.name === 'TimeoutError') {
      throw new APIError(
        'Request timed out. Category recommendations took too long. Please try again.',
        408
      );
    }

    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new APIError('Request was cancelled', 499);
    }

    // Unknown error
    throw new APIError(
      `Unexpected error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      500
    );
  }
}

