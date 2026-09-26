import React, { useState } from 'react';
import type { InspectionResponse, Violation } from '../types';

interface ResultsDashboardProps {
  result: InspectionResponse;
  onNewInspection: () => void;
}

export const ResultsDashboard: React.FC<ResultsDashboardProps> = ({ result, onNewInspection }) => {
  const [expandedRules, setExpandedRules] = useState<Record<string, boolean>>({});

  const toggleRuleExpand = (ruleId: string) => {
    setExpandedRules((prev) => ({ ...prev, [ruleId]: !prev[ruleId] }));
  };

  const { compliance, product, declarations, verification, inspection_id, generated_at, file, context, shelf_life } = result;

  const formatFieldName = (field: string) => {
    if (field === 'best_before' || field === 'shelf_life') return 'Best Before / Use By / Expiry';
    return field
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (l) => l.toUpperCase());
  };

  const formatVal = (field: string, val: unknown) => {
    if (val === null || val === undefined || val === '') {
      return 'Not detected';
    }
    if (typeof val === 'boolean') {
      return val ? 'Yes' : 'No';
    }
    if (field === 'category_confidence' && typeof val === 'number') {
      return `${Math.round(val * 100)}%`;
    }
    return String(val);
  };

  const getStatusDisplay = (status: string) => {
    switch (status) {
      case 'no_detected_violation':
        return {
          label: 'No detected violation',
          badgeClass: 'status-pill-pass',
          subtext: 'All required mandatory package declarations were detected cleanly.',
        };
      case 'requires_human_verification':
        return {
          label: 'Review required',
          badgeClass: 'status-pill-warning',
          subtext: 'Declarations detected; certain attributes require physical package check or contextual review.',
        };
      default:
        return {
          label: 'Potential issue detected',
          badgeClass: 'status-pill-issue',
          subtext: 'One or more mandatory package declarations were not detected.',
        };
    }
  };

  const statusDisplay = getStatusDisplay(compliance.status);
  const violations = compliance.violations || [];
  const passed = compliance.passed || [];
  const humanVerify = compliance.human_verification || [];
  const visualChecks = compliance.visual_checks || [];
  const rulesSummary = compliance.rules_summary || {
    total_rules: 0,
    applicable: 0,
    not_applicable: 0,
    requires_context: 0,
  };

  const formattedGeneratedDate = generated_at
    ? new Date(generated_at).toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      })
    : new Date().toLocaleString();

  const handlePrint = () => {
    const originalTitle = document.title;
    document.title = `LegalCheck Compliance Report - ${inspection_id || 'Inspection'}`;
    window.print();
    document.title = originalTitle;
  };

  // Determine merged shelf life value
  const shelfLifeDisplayValue =
    shelf_life?.raw_text ||
    shelf_life?.value ||
    declarations.best_before ||
    declarations.use_by ||
    declarations.expiry ||
    null;

  // Package Type formatted text
  const packageTypeRaw = product.package_type || context.package_type || declarations.package_type || 'single_package';
  const packageTypeLabel = String(packageTypeRaw).replaceAll('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());

  // Determine status for Unit Sale Price in Additional Declarations
  const getUnitSalePriceStatus = () => {
    if (['combination_package', 'group_package', 'multi_piece_package'].includes(packageTypeRaw)) {
      return { status: 'Not required', badgeClass: 'pill-neutral', note: 'Rule 6(11) 2023 Amendment Exemption' };
    }
    if (declarations.unit_sale_price) {
      return { status: 'Detected', badgeClass: 'pill-success', note: 'Rule 6(11) Compliant' };
    }
    return { status: 'Requires verification', badgeClass: 'pill-warning', note: 'Rule 6(11) Contextual Check' };
  };

  // Determine status for Country of Origin in Additional Declarations
  const getCountryOfOriginStatus = () => {
    if (declarations.country_of_origin) {
      return { status: 'Detected', badgeClass: 'pill-success', note: 'Rule 6(1)(aa) Compliant' };
    }
    if (context.is_imported === false) {
      return { status: 'Not applicable', badgeClass: 'pill-neutral', note: 'Verified Domestic Product' };
    }
    if (context.is_imported === true) {
      return { status: 'Potential issue', badgeClass: 'pill-danger', note: 'Rule 6(1)(aa) Imported Product' };
    }
    return { status: 'Requires verification', badgeClass: 'pill-warning', note: 'Import Status Unverified' };
  };

  const uspStatus = getUnitSalePriceStatus();
  const cooStatus = getCountryOfOriginStatus();

  // Filter Primary Declarations (Exclude unit_sale_price, country_of_origin, use_by, expiry, package_type, etc.)
  const primaryFieldsOrder = [
    'product_name',
    'manufacturer',
    'manufactured_for',
    'net_quantity',
    'mrp',
    'manufacturing_date',
    'shelf_life',
    'consumer_care',
  ];

  return (
    <div className="results-container">
      {/* Printable Report Layout (visible only when window.print() is called) */}
      <div className="print-report-wrapper">
        <div className="print-header">
          <div className="print-brand-block">
            <h1 className="print-logo">LEGALCHECK</h1>
            <p className="print-subtitle">Package Inspection Report (Legal Metrology Rules 2011)</p>
          </div>
          <div className="print-meta-block">
            <p><strong>Inspection ID:</strong> {inspection_id || 'N/A'}</p>
            <p><strong>Inspection Type:</strong> {result.inspection_type === 'digital' ? 'Digital Product Inspection' : 'Package Image Inspection'}</p>
            <p><strong>Date & Time:</strong> {formattedGeneratedDate}</p>
            <p><strong>Package Type:</strong> {packageTypeLabel}</p>
            {result.source?.url && <p><strong>Source URL:</strong> {result.source.url}</p>}
            {file?.filename && <p><strong>Source File:</strong> {file.filename}</p>}
          </div>
        </div>

        <div className="print-divider" />

        <div className="print-section">
          <h2 className="print-section-heading">Product Overview</h2>
          <table className="print-table">
            <tbody>
              <tr>
                <td><strong>Product Name:</strong></td>
                <td>{product.name || declarations.product_name || 'Unidentified Package'}</td>
                <td><strong>Category:</strong></td>
                <td>
                  {product.category || 'General Commodity'}
                  {product.category_confidence != null ? ` (${Math.round(product.category_confidence * 100)}% match)` : ''}
                </td>
              </tr>
              <tr>
                <td><strong>Package Type:</strong></td>
                <td>{packageTypeLabel}</td>
                <td><strong>Import Status:</strong></td>
                <td>{context.is_imported === true ? 'Imported' : context.is_imported === false ? 'Domestic' : 'Unverified'}</td>
              </tr>
              <tr>
                <td><strong>Overall Status:</strong></td>
                <td colSpan={3}>
                  <strong className={`print-status-text ${compliance.status}`}>
                    {statusDisplay.label.toUpperCase()}
                  </strong>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="print-section">
          <h2 className="print-section-heading">Compliance Summary</h2>
          <table className="print-table print-table-bordered">
            <thead>
              <tr>
                <th>Total Rules</th>
                <th>Applicable</th>
                <th>Passed Checks</th>
                <th>Potential Issues</th>
                <th>Requires Verification</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{rulesSummary.total_rules}</td>
                <td>{rulesSummary.applicable}</td>
                <td>{passed.length}</td>
                <td>{violations.length}</td>
                <td>{humanVerify.length + visualChecks.length}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="print-section">
          <h2 className="print-section-heading">Primary Package Declarations</h2>
          <table className="print-table print-table-striped">
            <thead>
              <tr>
                <th>Declaration Field</th>
                <th>Detected Value</th>
                <th>Legal Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Product Name</td>
                <td>{declarations.product_name || 'Not detected'}</td>
                <td>{declarations.product_name ? 'PRESENT' : 'NOT DETECTED'}</td>
              </tr>
              <tr>
                <td>Manufacturer / Packer / Importer</td>
                <td>{declarations.manufacturer || declarations.manufactured_for || 'Not detected'}</td>
                <td>{declarations.manufacturer || declarations.manufactured_for ? 'PRESENT' : 'NOT DETECTED'}</td>
              </tr>
              <tr>
                <td>Net Quantity</td>
                <td>{declarations.net_quantity || 'Not detected'}</td>
                <td>{declarations.net_quantity ? 'PRESENT' : 'NOT DETECTED'}</td>
              </tr>
              <tr>
                <td>MRP (Incl. of all taxes)</td>
                <td>{declarations.mrp || 'Not detected'}</td>
                <td>{declarations.mrp ? 'PRESENT' : 'NOT DETECTED'}</td>
              </tr>
              <tr>
                <td>Mfg / Packing Date</td>
                <td>{declarations.manufacturing_date || 'Not detected'}</td>
                <td>{declarations.manufacturing_date ? 'PRESENT' : 'NOT DETECTED'}</td>
              </tr>
              <tr>
                <td>Best Before / Use By / Expiry</td>
                <td>{shelfLifeDisplayValue || 'Not detected'}</td>
                <td>{shelfLifeDisplayValue ? 'PRESENT' : (context.has_shelf_life ? 'NOT DETECTED' : 'NOT APPLICABLE')}</td>
              </tr>
              <tr>
                <td>Consumer Care Details</td>
                <td>{declarations.consumer_care || 'Not detected'}</td>
                <td>{declarations.consumer_care ? 'PRESENT' : 'NOT DETECTED'}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div className="print-section print-page-break-inside-avoid">
          <h2 className="print-section-heading">Additional Applicable Declarations</h2>
          <table className="print-table print-table-bordered">
            <thead>
              <tr>
                <th>Declaration</th>
                <th>Detected Value</th>
                <th>Status</th>
                <th>Legal Reference</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Unit Sale Price</td>
                <td>{declarations.unit_sale_price || 'N/A'}</td>
                <td>{uspStatus.status.toUpperCase()}</td>
                <td>Rule 6(11) / 2023 Exemption Amendment</td>
              </tr>
              <tr>
                <td>Country of Origin</td>
                <td>{declarations.country_of_origin || 'N/A'}</td>
                <td>{cooStatus.status.toUpperCase()}</td>
                <td>Rule 6(1)(aa) (Imported Products)</td>
              </tr>
            </tbody>
          </table>
        </div>

        {violations.length > 0 && (
          <div className="print-section print-page-break-inside-avoid">
            <h2 className="print-section-heading">Potential Findings & Issues ({violations.length})</h2>
            <table className="print-table print-table-bordered">
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Field</th>
                  <th>Requirement</th>
                  <th>Detected Value</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {violations.map((item: Violation) => (
                  <tr key={item.rule_id}>
                    <td>{item.rule_id} ({item.rule_number})</td>
                    <td>{formatFieldName(item.field)}</td>
                    <td>{item.requirement}</td>
                    <td>{item.detected_value ?? 'Not detected'}</td>
                    <td>{item.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="print-footer-notice">
          <p>
            <strong>Human Verification Notice:</strong> AI-assisted screening result. Findings should be verified by a qualified person before legal or enforcement action under the Legal Metrology (Packaged Commodities) Rules, 2011.
          </p>
        </div>
      </div>

      {/* Interactive Web Header Summary & Action Buttons */}
      <div className="results-header-card print-hide">
        <div className="results-header-left">
          <div className="results-title-group">
            <h2 className="result-product-title">
              {product.name || declarations.product_name || 'Package Label Inspection'}
            </h2>
            <div className="result-meta-tags">
              {result.inspection_type === 'digital' && (
                <span className="meta-digital-tag">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 4 }}>
                    <circle cx="12" cy="12" r="10" />
                    <line x1="2" y1="12" x2="22" y2="12" />
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
                  </svg>
                  Digital Inspection
                </span>
              )}
              <span className="meta-category-tag">{product.category || 'General Commodity'}</span>
              <span className="meta-pkgtype-tag">{packageTypeLabel}</span>
              {product.category_confidence != null && (
                <span className="meta-conf-tag">{Math.round(product.category_confidence * 100)}% match</span>
              )}
            </div>
          </div>
          {result.source?.url && (
            <div className="web-source-bar">
              <span className="web-source-label">Source URL:</span>
              <a href={result.source.url} target="_blank" rel="noopener noreferrer" className="web-source-link">
                {result.source.url}
              </a>
            </div>
          )}
          <p className="result-header-subtext">{statusDisplay.subtext}</p>
        </div>

        <div className="results-header-right">
          <div className={`status-pill ${statusDisplay.badgeClass}`}>
            <span className="status-dot"></span>
            {statusDisplay.label}
          </div>

          <div className="results-actions-group">
            <button type="button" className="btn-print-action" onClick={handlePrint}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polyline points="6 9 6 2 18 2 18 9" />
                <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2" />
                <rect x="6" y="14" width="12" height="8" />
              </svg>
              Print report
            </button>

            <button type="button" className="btn-secondary-sm" onClick={onNewInspection}>
              New inspection
            </button>
          </div>
        </div>
      </div>

      {/* Primary Package Declarations Grid */}
      <section className="results-section print-hide">
        <div className="section-title-row">
          <h3 className="section-heading">Mandatory Package Declarations</h3>
          <span className="section-subheading">Key primary declarations extracted from package image(s)</span>
        </div>

        <div className="declarations-compact-grid">
          {primaryFieldsOrder.map((field) => {
            let val: unknown = declarations[field];
            if (field === 'shelf_life') {
              val = shelfLifeDisplayValue;
            }

            const isMissing = val === null || val === undefined || val === '';
            return (
              <div key={field} className={`decl-item-box ${isMissing ? 'missing' : 'present'}`}>
                <span className="decl-key-name">{formatFieldName(field)}</span>
                <span className={`decl-val-text ${isMissing ? 'val-missing' : ''}`}>
                  {formatVal(field, val)}
                </span>
                {field === 'shelf_life' && (
                  <span className="decl-legal-note">Rule 6(1)(da)</span>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* Additional Applicable Declarations Section */}
      <section className="results-section print-hide">
        <div className="section-title-row">
          <h3 className="section-heading">Additional Applicable Declarations</h3>
          <span className="section-subheading">Specific contextual declarations under Legal Metrology Rules</span>
        </div>

        <div className="additional-declarations-grid">
          {/* Unit Sale Price Card */}
          <div className="additional-decl-card">
            <div className="add-decl-header">
              <div className="add-decl-title-block">
                <h4 className="add-decl-name">Unit Sale Price</h4>
                <span className="add-decl-cite">Rule 6(11) & 2023 Amendment</span>
              </div>
              <span className={`add-decl-pill ${uspStatus.badgeClass}`}>
                {uspStatus.status}
              </span>
            </div>
            <div className="add-decl-body">
              <span className="add-decl-value">
                {declarations.unit_sale_price || 'Not declared on package'}
              </span>
              <p className="add-decl-note">{uspStatus.note}</p>
            </div>
          </div>

          {/* Country of Origin Card */}
          <div className="additional-decl-card">
            <div className="add-decl-header">
              <div className="add-decl-title-block">
                <h4 className="add-decl-name">Country of Origin</h4>
                <span className="add-decl-cite">Rule 6(1)(aa)</span>
              </div>
              <span className={`add-decl-pill ${cooStatus.badgeClass}`}>
                {cooStatus.status}
              </span>
            </div>
            <div className="add-decl-body">
              <span className="add-decl-value">
                {declarations.country_of_origin || (context.is_imported === false ? 'Verified Domestic Product' : 'Not declared')}
              </span>
              <p className="add-decl-note">{cooStatus.note}</p>
            </div>
          </div>
        </div>
      </section>

      {/* Compliance Findings Section */}
      {violations.length > 0 && (
        <section className="results-section print-hide">
          <div className="section-title-row">
            <h3 className="section-heading">Potential Issues & Findings ({violations.length})</h3>
            <span className="section-subheading">Mandatory items that require attention or verification</span>
          </div>

          <div className="findings-list">
            {violations.map((item: Violation) => {
              const isExpanded = !!expandedRules[item.rule_id];
              return (
                <div key={item.rule_id} className="finding-card">
                  <div className="finding-card-header">
                    <div className="finding-title-block">
                      <span className="finding-field-label">{formatFieldName(item.field)}</span>
                      <h4 className="finding-summary">{item.description}</h4>
                    </div>
                    <span className="finding-verification-badge">Requires human verification</span>
                  </div>

                  <div className="finding-details-list">
                    <div className="finding-detail-row">
                      <span className="detail-label">Detected value:</span>
                      <span className="detail-value">{item.detected_value ?? 'Not detected'}</span>
                    </div>

                    <div className="finding-detail-row">
                      <span className="detail-label">Requirement:</span>
                      <span className="detail-value">{item.requirement}</span>
                    </div>

                    <div className="finding-detail-row">
                      <span className="detail-label">Evidence:</span>
                      <span className="detail-value">{item.evidence}</span>
                    </div>
                  </div>

                  <div className="finding-expandable">
                    <button
                      type="button"
                      className="btn-toggle-rule"
                      onClick={() => toggleRuleExpand(item.rule_id)}
                    >
                      <span>{isExpanded ? 'Hide rule details' : 'Why was this flagged?'}</span>
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        style={{ transform: isExpanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.15s ease' }}
                      >
                        <polyline points="6 9 12 15 18 9" />
                      </svg>
                    </button>

                    {isExpanded && (
                      <div className="rule-expanded-box">
                        <div className="rule-meta-line">
                          <span><strong>Rule ID:</strong> {item.rule_id}</span>
                          <span><strong>Rule reference:</strong> {item.rule_number}</span>
                        </div>
                        <p className="rule-source-line"><strong>Source:</strong> {item.source}</p>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Human Verification & Visual Review Section */}
      {(humanVerify.length > 0 || visualChecks.length > 0) && (
        <section className="results-section print-hide">
          <div className="section-title-row">
            <h3 className="section-heading">Items Requiring Review</h3>
            <span className="section-subheading">Contextual or physical layout checks</span>
          </div>

          <div className="verification-items-list">
            {humanVerify.map((hv) => (
              <div key={hv.rule_id} className="review-item-card">
                <span className="review-tag">Context check</span>
                <div className="review-content">
                  <strong>{formatFieldName(hv.field)}</strong>
                  <p>{hv.reason}</p>
                </div>
              </div>
            ))}

            {visualChecks.map((vc) => (
              <div key={vc.rule_id} className="review-item-card">
                <span className="review-tag">Visual check</span>
                <div className="review-content">
                  <strong>{formatFieldName(vc.field)} ({vc.rule_number})</strong>
                  <p>{vc.requirement}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Verified Declarations Section */}
      {passed.length > 0 && (
        <section className="results-section print-hide">
          <div className="section-title-row">
            <h3 className="section-heading">Verified Declarations ({passed.length})</h3>
            <span className="section-subheading">Declarations present and matching configured rules</span>
          </div>

          <div className="passed-simple-grid">
            {passed.map((p) => (
              <div key={p.rule_id} className="passed-chip">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                <span className="passed-chip-label">{formatFieldName(p.field)}:</span>
                <strong className="passed-chip-val">{p.detected_value}</strong>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Verification Disclaimer */}
      <div className="verification-disclaimer-box print-hide">
        <p>
          <strong>AI-assisted screening result.</strong> LegalCheck provides screening based on computer vision extraction. 
          {verification?.message || ' Findings should be verified by a qualified person before legal or enforcement action.'}
        </p>
      </div>
    </div>
  );
};
