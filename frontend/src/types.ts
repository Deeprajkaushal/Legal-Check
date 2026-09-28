export type ShelfLifeData = {
  value: string | null;
  type: 'best_before' | 'use_by' | 'expiry' | 'unknown' | null;
  raw_text: string | null;
};

export type ExtractedData = {
  product_name: string | null;
  manufacturer: string | null;
  manufactured_for: string | null;
  net_quantity: string | null;
  unit_sale_price: string | null;
  mrp: string | null;
  manufacturing_date: string | null;
  best_before: string | null;
  use_by?: string | null;
  expiry?: string | null;
  shelf_life?: ShelfLifeData | null;
  country_of_origin: string | null;
  consumer_care: string | null;
  product_category: string | null;
  category_confidence: number | null;
  category_evidence?: string[] | null;
  package_type?: 'single_package' | 'combination_package' | 'group_package' | 'multi_piece_package' | 'unknown';
  is_imported: boolean | null;
  has_shelf_life: boolean | null;
  [key: string]: unknown;
};

export type Violation = {
  rule_id: string;
  rule_number: string;
  field: string;
  detected_value: string | null;
  description: string;
  requirement: string;
  source: string;
  evidence: string;
  confidence: string;
  verification_status?: string;
};

export type PassedCheck = {
  rule_id: string;
  rule_number: string;
  field: string;
  detected_value: string | null;
  status: string;
};

export type ApplicableRule = {
  rule_id: string;
  rule_number: string;
  field: string;
  requirement: string;
  check_type: string;
  source: string;
};

export type NotApplicableRule = {
  rule_id: string;
  field: string;
  reason: string;
};

export type RequiresContextItem = {
  rule_id: string;
  field: string;
  description?: string;
  reason: string;
  verification_status?: string;
};

export type HumanVerificationItem = {
  rule_id: string;
  field: string;
  description: string;
  reason: string;
  verification_status: string;
};

export type VisualCheckItem = {
  rule_id: string;
  rule_number: string;
  field: string;
  status: string;
  requirement: string;
  source: string;
};

export type ComplianceResult = {
  status: string;
  rules_summary: {
    total_rules: number;
    applicable: number;
    not_applicable: number;
    requires_context: number;
  };
  applicable_rules: ApplicableRule[];
  passed: PassedCheck[];
  violations: Violation[];
  not_applicable: NotApplicableRule[];
  requires_context: RequiresContextItem[];
  human_verification: HumanVerificationItem[];
  visual_checks: VisualCheckItem[];
};

export type OcrEvidenceItem = {
  field: string;
  label: string;
  detected_value: string;
  source_image: string;
  ocr_snippet: string;
  confidence: number;
  bounding_box?: unknown;
};

export type OcrDebugInfo = {
  images_processed: number;
  ocr_status: string;
  gemini_text_only: boolean;
  combined_ocr_text?: string;
  per_image_ocr?: {
    image_index: number;
    line_count: number;
    avg_confidence: number;
    text_preview: string;
  }[];
  ocr_evidence?: OcrEvidenceItem[];
  timing?: {
    upload_ms?: number;
    ocr_ms?: number;
    gemini_ms?: number;
    compliance_ms?: number;
    report_ms?: number;
    total_ms?: number;
  };
};

export type InspectionResponse = {
  inspection_id: string;
  inspection_type?: 'package' | 'digital';
  source?: {
    type: string;
    url?: string;
    domain?: string;
    page_title?: string;
    filename?: string;
    [key: string]: unknown;
  };
  generated_at: string;
  project?: string;
  problem_id?: string;
  file?: {
    filename: string;
    content_type: string;
  };
  product: {
    name: string | null;
    category: string | null;
    category_confidence: number | null;
    category_evidence?: string[] | null;
    package_type?: string;
  };
  context: {
    is_imported: boolean | null;
    has_shelf_life: boolean | null;
    package_type?: string;
  };
  shelf_life?: ShelfLifeData | null;
  declarations: ExtractedData;
  compliance: ComplianceResult;
  verification: {
    status: string;
    message: string;
  };
  legal_references?: Record<string, string>;
  ocr_debug?: OcrDebugInfo;
};

export type SelectedImage = {
  id: string;
  file: File;
  previewUrl: string;
};

export type AppState = 'initial' | 'camera_open' | 'image_ready' | 'inspecting' | 'success' | 'error';
export type ActiveTab = 'inspect' | 'history' | 'about';

export type HistoryItem = {
  id: string;
  timestamp: string;
  formattedDate: string;
  productName: string;
  category: string;
  status: string;
  violationsCount: number;
  thumbnailUrl?: string;
  inspectionType?: 'package' | 'digital';
  result: InspectionResponse;
};
