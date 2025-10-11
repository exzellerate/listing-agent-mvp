export type Platform = 'ebay' | 'amazon' | 'walmart';

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
}

export interface ErrorResponse {
  error: string;
  detail?: string;
}
