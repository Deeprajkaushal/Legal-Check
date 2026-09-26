import type {
  InspectionResponse,
  ExtractedData,
  ApplicableRule,
  Violation,
  PassedCheck,
  HumanVerificationItem,
  VisualCheckItem,
  NotApplicableRule,
  RequiresContextItem,
  ShelfLifeData,
} from '../types';

export const combineInspectionResults = (
  responses: InspectionResponse[],
  imageCount: number
): InspectionResponse => {
  if (responses.length === 0) {
    throw new Error('No inspection responses to combine.');
  }

  if (responses.length === 1) {
    return responses[0];
  }

  // 1. Merge Extracted Declarations
  const combinedDeclarations: ExtractedData = {
    product_name: null,
    manufacturer: null,
    manufactured_for: null,
    net_quantity: null,
    unit_sale_price: null,
    mrp: null,
    manufacturing_date: null,
    best_before: null,
    use_by: null,
    expiry: null,
    shelf_life: null,
    country_of_origin: null,
    consumer_care: null,
    product_category: null,
    category_confidence: null,
    package_type: 'unknown',
    is_imported: null,
    has_shelf_life: null,
  };

  const allKeys = new Set<string>();
  responses.forEach((resp) => {
    if (resp.declarations) {
      Object.keys(resp.declarations).forEach((k) => allKeys.add(k));
    }
  });

  allKeys.forEach((key) => {
    let bestVal: unknown = null;

    for (const resp of responses) {
      const val = resp.declarations?.[key];
      if (val === null || val === undefined || val === '') continue;

      if (typeof val === 'boolean') {
        if (val === true) {
          bestVal = true;
          break;
        } else if (bestVal === null) {
          bestVal = false;
        }
      } else if (typeof val === 'number') {
        if (bestVal === null || (typeof bestVal === 'number' && val > bestVal)) {
          bestVal = val;
        }
      } else if (typeof val === 'string') {
        const trimmed = val.trim();
        if (trimmed) {
          if (!bestVal || (typeof bestVal === 'string' && trimmed.length > bestVal.trim().length)) {
            bestVal = trimmed;
          }
        }
      } else if (typeof val === 'object') {
        bestVal = val;
      }
    }

    combinedDeclarations[key] = bestVal;
  });

  // Merge Shelf Life data
  let combinedShelfLife: ShelfLifeData | null = null;
  for (const resp of responses) {
    if (resp.shelf_life?.raw_text || resp.declarations?.shelf_life?.raw_text) {
      combinedShelfLife = resp.shelf_life || (resp.declarations.shelf_life as ShelfLifeData);
      break;
    }
  }
  combinedDeclarations.shelf_life = combinedShelfLife;

  // 2. Merge Product & Context Details
  let productName: string | null = null;
  let category: string | null = null;
  let maxConfidence: number | null = null;
  let packageType = 'unknown';

  for (const resp of responses) {
    if (!productName && resp.product?.name) {
      productName = resp.product.name;
    }
    if (!category && resp.product?.category) {
      category = resp.product.category;
    }
    if (resp.product?.category_confidence != null) {
      if (maxConfidence === null || resp.product.category_confidence > maxConfidence) {
        maxConfidence = resp.product.category_confidence;
      }
    }
    if (resp.product?.package_type && resp.product.package_type !== 'unknown') {
      packageType = resp.product.package_type;
    }
  }

  let isImported: boolean | null = null;
  let hasShelfLife: boolean | null = null;

  for (const resp of responses) {
    if (resp.context?.is_imported === true) isImported = true;
    else if (isImported === null && resp.context?.is_imported === false) isImported = false;

    if (resp.context?.has_shelf_life === true) hasShelfLife = true;
    else if (hasShelfLife === null && resp.context?.has_shelf_life === false) hasShelfLife = false;
  }

  // 3. Consolidate Rules & Compliance
  const ruleMap = new Map<string, ApplicableRule>();
  const notApplicableMap = new Map<string, NotApplicableRule>();
  const requiresContextMap = new Map<string, RequiresContextItem>();
  const visualChecksMap = new Map<string, VisualCheckItem>();
  const humanVerifyMap = new Map<string, HumanVerificationItem>();

  responses.forEach((resp) => {
    const comp = resp.compliance;
    if (!comp) return;

    comp.applicable_rules?.forEach((rule) => {
      if (!ruleMap.has(rule.rule_id)) ruleMap.set(rule.rule_id, rule);
    });

    comp.not_applicable?.forEach((item) => {
      if (!notApplicableMap.has(item.rule_id)) notApplicableMap.set(item.rule_id, item);
    });

    comp.requires_context?.forEach((item) => {
      if (!requiresContextMap.has(item.rule_id)) requiresContextMap.set(item.rule_id, item);
    });

    comp.visual_checks?.forEach((item) => {
      if (!visualChecksMap.has(item.rule_id)) visualChecksMap.set(item.rule_id, item);
    });

    comp.human_verification?.forEach((item) => {
      if (!humanVerifyMap.has(item.rule_id)) humanVerifyMap.set(item.rule_id, item);
    });
  });

  // Re-evaluate violations vs passed based on aggregated declarations
  const passed: PassedCheck[] = [];
  const violations: Violation[] = [];

  ruleMap.forEach((rule) => {
    const field = rule.field;
    const value = combinedDeclarations[field];
    const isPresent = value !== null && value !== undefined && String(value).trim() !== '';

    if (rule.check_type === 'visual') {
      return;
    }

    if (field === 'unit_sale_price') {
      if (isPresent) {
        passed.push({
          rule_id: rule.rule_id,
          rule_number: rule.rule_number,
          field,
          detected_value: String(value),
          status: 'detected',
        });
      }
      // Never push unit_sale_price to violations
      return;
    }

    if (isPresent) {
      passed.push({
        rule_id: rule.rule_id,
        rule_number: rule.rule_number,
        field,
        detected_value: String(value),
        status: 'detected',
      });
    } else {
      violations.push({
        rule_id: rule.rule_id,
        rule_number: rule.rule_number,
        field,
        detected_value: null,
        description: `Required declaration '${field}' was not detected.`,
        requirement: rule.requirement,
        source: rule.source,
        evidence: `The declaration was not detected across the ${imageCount} package image(s) provided.`,
        confidence: 'requires_human_verification',
        verification_status: 'pending',
      });
    }
  });

  const humanVerificationList = Array.from(humanVerifyMap.values());
  const visualChecksList = Array.from(visualChecksMap.values());
  const applicableList = Array.from(ruleMap.values());
  const notApplicableList = Array.from(notApplicableMap.values());
  const requiresContextList = Array.from(requiresContextMap.values());

  let overallStatus = 'no_detected_violation';
  if (violations.length > 0) {
    overallStatus = 'potential_violation';
  } else if (humanVerificationList.length > 0 || visualChecksList.length > 0) {
    overallStatus = 'requires_human_verification';
  }

  const primaryResp = responses[0];

  return {
    inspection_id: primaryResp.inspection_id || `INSP-${Date.now().toString(36).toUpperCase()}`,
    generated_at: new Date().toISOString(),
    project: primaryResp.project || 'LegalCheck',
    problem_id: primaryResp.problem_id || 'SIH26034',
    file: {
      filename: `${imageCount} images inspected`,
      content_type: 'image/*',
    },
    product: {
      name: productName || (combinedDeclarations.product_name as string) || null,
      category: category || (combinedDeclarations.product_category as string) || null,
      category_confidence: maxConfidence,
      package_type: packageType,
    },
    context: {
      is_imported: isImported,
      has_shelf_life: hasShelfLife,
      package_type: packageType,
    },
    shelf_life: combinedShelfLife,
    declarations: combinedDeclarations,
    compliance: {
      status: overallStatus,
      rules_summary: {
        total_rules: applicableList.length + notApplicableList.length + requiresContextList.length,
        applicable: applicableList.length,
        not_applicable: notApplicableList.length,
        requires_context: requiresContextList.length,
      },
      applicable_rules: applicableList,
      passed,
      violations,
      not_applicable: notApplicableList,
      requires_context: requiresContextList,
      human_verification: humanVerificationList,
      visual_checks: visualChecksList,
    },
    verification: {
      status: overallStatus,
      message:
        overallStatus === 'potential_violation'
          ? 'Potential missing mandatory declaration(s) detected across package images.'
          : overallStatus === 'requires_human_verification'
          ? 'Package declarations detected. Certain attributes require contextual or physical verification.'
          : 'All required mandatory package declarations were detected across uploaded images.',
    },
    legal_references: primaryResp.legal_references || {
      shelf_life: 'Rule 6(1)(da): Best Before / Use By for applicable commodities',
      country_of_origin: 'Rule 6(1)(aa): Country of origin/manufacture/assembly for imported products',
      unit_sale_price: 'Rule 6(11): Unit Sale Price and its applicability',
    },
  };
};
