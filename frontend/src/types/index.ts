export type Platform = 'ebay' | 'amazon' | 'walmart';

export type CompletenessStatus = 'complete_set' | 'incomplete_set' | 'accessory_only' | 'single_from_pair' | 'unknown';

export interface FieldDiscrepancy {
  field_name: string;
  values: any[];
  confidence_impact: string;
}

export interface ImageAnalysis {
  image_index: number;
  product_name: string;
  brand: string | null;
  category: string | null;
  condition: string;
  color: string | null;
  material: string | null;
  model_number: string | null;
  key_features: string[];
  // Enhanced identification fields
  analysis_confidence: number;
  visible_components: string[];
  completeness_status: CompletenessStatus;
  missing_components: string[] | null;
  ambiguities: string[];
  reasoning: string | null;
}

// Category recommendation types
export interface CategoryRecommendation {
  category_id: string;
  category_name: string;
  category_path: string;
  confidence: number;
  reasoning: string;
}

// Aspect prediction types
export type AspectSource = 'visible' | 'inferred' | 'unknown';

export interface PredictedAspect {
  value: string;
  confidence: number;
  source: AspectSource;
}

export interface CategoryAspectAnalysis {
  predicted_aspects: Record<string, PredictedAspect>;
  auto_populate_fields: Record<string, string>;
  reasoning: string;
}

export interface CategoryAspectRequest {
  analysis_id: number;
  category_id: string;
}

export interface CategoryAspectResponse {
  analysis_id: number;
  category_id: string;
  category_name: string;
  aspect_analysis: CategoryAspectAnalysis;
}

// eBay Category types (from Claude analysis)
export interface EbayCategoryAlternative {
  category_id: string;
  category_name: string;
  rejection_reason: string;
}

export interface EbayCategory {
  category_id: string;
  category_name: string;
  category_path: string;
  tool_query_used?: string;
  alternatives_considered?: EbayCategoryAlternative[];
  selection_confidence?: number;
  selection_reasoning?: string;
}

// Aspect types for eBay category aspects
export interface AspectValue {
  value: string;
  value_id?: string;
}

export interface FormattedAspect {
  name: string;
  required: boolean;
  input_type: 'dropdown' | 'text';
  multi_select: boolean;
  data_type: string;
  usage: string;
  enabled_for_variations: boolean;
  values: AspectValue[];
  max_length?: number;
  applicable_to: string[];
}

export interface CategoryAspects {
  category_id: string;
  category_name: string;
  aspects: {
    required: FormattedAspect[];
    recommended: FormattedAspect[];
    optional: FormattedAspect[];
  };
  counts: {
    total: number;
    required: number;
    recommended: number;
    optional: number;
  };
}

export interface AnalysisResult {
  product_name: string;
  brand: string | null;
  category: string | null;
  condition: string;
  color: string | null;
  material: string | null;
  model_number: string | null;
  key_features: string[];
  suggested_title: string;
  suggested_description: string;
  // Multi-image analysis fields
  confidence_score: number;
  images_analyzed: number;
  individual_analyses: ImageAnalysis[];
  discrepancies: FieldDiscrepancy[];
  verification_notes: string | null;
  // Enhanced identification fields
  analysis_confidence: number;
  visible_components: string[];
  completeness_status: CompletenessStatus;
  missing_components: string[] | null;
  ambiguities: string[];
  reasoning: string | null;
  // Learning system field
  analysis_id?: number;
  // eBay category recommendations
  ebay_category_suggestions?: CategoryRecommendation[];
  // eBay category and aspects (new integrated workflow)
  suggested_category_id?: string;
  suggested_category_aspects?: CategoryAspects;
  // Product attributes from backend analysis
  product_attributes?: {
    Type?: string | null;
    Size?: string | null;
    Features?: string[] | null;
    Connectivity?: string | null;
    Power_Source?: string | null;
    Material?: string | null;
    Style?: string | null;
    additional_attributes?: Record<string, any>;
  };
  extracted_attributes?: Record<string, any>;
  // eBay category and aspects from Claude analysis
  ebay_category_keywords?: string[];
  ebay_category?: EbayCategory;
  ebay_aspects?: Record<string, string | string[]>;
}

export interface CompetitorListing {
  price: number;
  title: string;
  url: string | null;
  date_sold: string | null;
}

export interface PricingStatistics {
  min_price: number;
  max_price: number;
  average: number;
  median: number;
  suggested_price: number;
}

export interface PricingData {
  competitor_prices: CompetitorListing[];
  statistics: PricingStatistics;
  confidence_score: number;
  market_insights: string;
  timestamp: string;
}

export interface ErrorResponse {
  error: string;
  detail?: string;
}

// Testing Types
export interface FieldScore {
  expected: string | string[] | number[] | null;
  actual: string | string[] | number | null;
  score: number;
  passed: boolean;
  details: string;
}

export interface TestItemResult {
  test_id: number;
  image_path: string;
  status: 'passed' | 'failed' | 'error';
  overall_score: number;
  duration_seconds: number;
  timestamp?: string;  // ISO 8601 timestamp when test was run
  error_type?: string;  // Type of error (file_not_found, analysis_error, etc.)
  error_details?: string;  // Detailed error message
  error_traceback?: string;  // Full traceback for debugging
  analysis: {
    [field: string]: FieldScore;
  };
}

export interface TestBatchSummary {
  total_tests: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
  total_duration_seconds: number;
  field_accuracy: {
    [field: string]: number;
  };
  failed_tests: Array<{
    test_id: number;
    image_path: string;
    overall_score: number;
    failed_fields: string[];
  }>;
}

export interface TestBatchResponse {
  summary: TestBatchSummary;
  results: TestItemResult[];
}

// Learning System Types
export type UserAction = 'accepted' | 'edited' | 'corrected' | 'rejected';

export interface ConfirmAnalysisRequest {
  analysis_id: number;
  user_action: UserAction;
  user_product_name?: string;
  user_brand?: string;
  user_category?: string;
  user_title?: string;
  user_description?: string;
  user_price?: number;
  user_notes?: string;
}

export interface ConfirmAnalysisResponse {
  success: boolean;
  message: string;
  analysis_id: number;
}

export interface LearningStats {
  // Daily stats
  analyses_today: number;
  api_calls_today: number;
  api_calls_saved_today: number;
  // Cumulative stats
  total_analyses: number;
  total_api_calls: number;
  total_api_calls_saved: number;
  // Quality metrics
  acceptance_rate: number;
  average_confidence: number;
  // Cost savings
  estimated_savings_today: number;
  estimated_total_savings: number;
  // Learning system stats
  learned_products_count: number;
  pending_analyses: number;
}

// Draft Listing Types
export interface DraftListing {
  id: number;
  analysis_id: number | null;
  user_id: string;
  title: string;
  description: string;
  price: number | null;
  platform: Platform;
  product_name: string | null;
  brand: string | null;
  category: string | null;
  condition: string | null;
  color: string | null;
  material: string | null;
  model_number: string | null;
  features: string[] | null;
  keywords: string[] | null;
  image_paths: string[] | null;
  extra_data: Record<string, any> | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface DraftListingSummary {
  id: number;
  title: string;
  price: number | null;
  platform: Platform;
  product_name: string | null;
  brand: string | null;
  image_paths: string[] | null;
  created_at: string;
  updated_at: string;
}

export interface CreateDraftRequest {
  analysis_id?: number;
  title: string;
  description: string;
  price?: number;
  platform: Platform;
  product_name?: string;
  brand?: string;
  category?: string;
  condition?: string;
  color?: string;
  material?: string;
  model_number?: string;
  features?: string[];
  keywords?: string[];
  image_paths?: string[];
  extra_data?: Record<string, any>;
  notes?: string;
}

// Listing Management Types
export interface ListingMetrics {
  views: number;
  watchers: number;
}

export interface ListingSummary {
  id: number;
  sku: string;
  listing_id: string | null;
  title: string;
  price: number;
  image_urls: string[] | null;
  status: string;
  ebay_status: string | null;
  metrics: ListingMetrics;
  ebay_listing_url: string | null;
  published_at: string | null;
  sold_quantity: number;
  sold_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ListingsResponse {
  listings: ListingSummary[];
  total: number;
  page: number;
  limit: number;
}

export interface SyncResponse {
  listings_synced: number;
  metrics_updated: number;
  orders_processed: number;
  listings_updated: number;
  errors: string[];
}
