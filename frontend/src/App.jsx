import React, { useState, useEffect, useRef } from 'react';
import { checkHealth, scanImage } from './api';
import { mapBbox } from './utils/bbox';

export default function App() {
  const [status, setStatus] = useState('Checking...');
  const [file, setFile] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Context Form State
  const [packageType, setPackageType] = useState('retail');
  const [category, setCategory] = useState('general');
  const [isImport, setIsImport] = useState(false);

  // UI state
  const [showRawOcr, setShowRawOcr] = useState(false);
  const [useHindi, setUseHindi] = useState(false);
  const [selectedRuleId, setSelectedRuleId] = useState(null);
  const [expandedRuleId, setExpandedRuleId] = useState(null);
  const [showNaAccordion, setShowNaAccordion] = useState(false);

  const canvasRef = useRef(null);

  useEffect(() => {
    checkHealth()
      .then(() => setStatus('Backend online'))
      .catch(() => setStatus('Backend offline'));
  }, []);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setImageSrc(URL.createObjectURL(selected));
      setScanResult(null);
      setSelectedRuleId(null);
    }
  };

  const handleScan = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await scanImage(file, {
        packageType,
        category,
        isImport,
      });
      setScanResult(data);
    } catch (err) {
      setErrorMsg('Error scanning label. Ensure format is JPEG/PNG/WebP and under 10 MB.');
    } finally {
      setLoading(false);
    }
  };

  // Render Canvas Evidence Overlay
  useEffect(() => {
    if (!scanResult || !imageSrc || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = imageSrc;

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx.drawImage(img, 0, 0);

      const ocrImageSize = scanResult.ocr?.image_size || { width: img.width, height: img.height };
      const drawnSize = { width: canvas.width, height: canvas.height };

      const findings = scanResult.findings || [];
      findings.forEach((finding) => {
        if (!finding.evidence_bbox || finding.verdict === 'N/A') return;
        const bbox = finding.evidence_bbox;
        const isSelected = selectedRuleId === finding.rule_id;

        const mappedBox = mapBbox(bbox, ocrImageSize, drawnSize);
        if (!mappedBox) return;
        
        const [minX, minY, maxX, maxY] = mappedBox;

        const width = maxX - minX;
        const height = maxY - minY;

        let strokeColor = '#10b981';
        let fillColor = 'rgba(16, 185, 129, 0.15)';
        if (finding.verdict === 'FAIL') {
          strokeColor = '#ef4444';
          fillColor = 'rgba(239, 68, 68, 0.2)';
        } else if (finding.verdict === 'NEEDS_REVIEW') {
          strokeColor = '#f59e0b';
          fillColor = 'rgba(245, 158, 11, 0.2)';
        }

        ctx.fillStyle = fillColor;
        ctx.fillRect(minX, minY, width, height);

        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = isSelected ? 6 : 3;
        ctx.strokeRect(minX, minY, width, height);

        if (isSelected) {
          ctx.strokeStyle = '#ffffff';
          ctx.lineWidth = 2;
          ctx.strokeRect(minX - 2, minY - 2, width + 4, height + 4);
        }

        // Draw Rule Tag Label
        ctx.fillStyle = strokeColor;
        const labelText = finding.rule_id;
        ctx.font = 'bold 16px sans-serif';
        const textMetrics = ctx.measureText(labelText);
        const padding = 4;
        const labelHeight = 22;
        const labelWidth = textMetrics.width + padding * 2;

        ctx.fillRect(minX, Math.max(0, minY - labelHeight), labelWidth, labelHeight);
        ctx.fillStyle = '#ffffff';
        ctx.fillText(labelText, minX + padding, Math.max(16, minY - 5));
      });
    };
  }, [scanResult, imageSrc, selectedRuleId]);

  const downloadCanvasImage = () => {
    if (!canvasRef.current) return;
    const link = document.createElement('a');
    link.download = `nirikshan_evidence_${scanResult?.filename || 'scan'}.png`;
    link.href = canvasRef.current.toDataURL('image/png');
    link.click();
  };

  const isOnline = status === 'Backend online';

  const renderFieldValue = (key, field) => {
    if (!field) return null;
    if (key === 'net_quantity') {
      let str = `${field.value ?? ''} ${field.unit ?? ''}`.trim() || field.raw;
      if (field.count) str += ` (Count: ${field.count})`;
      return str;
    }
    if (key === 'mrp') {
      let str = field.value !== null ? `${field.currency === 'INR' ? '₹' : ''}${field.value}` : field.raw;
      if (field.incl_taxes_phrase) str += ' (Incl. of all taxes)';
      return str;
    }
    if (key === 'unit_sale_price') {
      return field.value !== null ? `₹${field.value} / ${field.per_unit || ''}` : field.raw;
    }
    if (key === 'mfg_date' || key === 'best_before') {
      if (field.duration_months) return `${field.duration_months} Months`;
      if (field.month && field.year) {
        return `${field.day ? field.day + '/' : ''}${field.month}/${field.year}`;
      }
      return field.raw;
    }
    if (key === 'consumer_care') {
      let parts = [];
      if (field.phone) parts.push(`Phone: ${field.phone}`);
      if (field.email) parts.push(`Email: ${field.email}`);
      if (field.address) parts.push(field.address);
      return parts.join(' | ') || field.raw || field.value;
    }
    if (typeof field === 'object') {
      return field.value || field.name || field.address || field.raw;
    }
    return String(field);
  };

  const declarationFields = [
    { key: 'generic_name', label: 'Generic Name' },
    { key: 'net_quantity', label: 'Net Quantity' },
    { key: 'mrp', label: 'MRP' },
    { key: 'unit_sale_price', label: 'Unit Sale Price' },
    { key: 'mfg_date', label: 'Mfg / Pkd Date' },
    { key: 'best_before', label: 'Best Before / Expiry' },
    { key: 'country_of_origin', label: 'Country of Origin' },
    { key: 'manufacturer', label: 'Manufacturer' },
    { key: 'packer', label: 'Packer' },
    { key: 'importer', label: 'Importer' },
    { key: 'marketer', label: 'Marketer' },
    { key: 'consumer_care', label: 'Consumer Care' },
  ];

  const applicableFindings = scanResult?.findings?.filter((f) => f.verdict !== 'N/A') || [];
  const naFindings = scanResult?.findings?.filter((f) => f.verdict === 'N/A') || [];

  return (
    <div className="container">
      <header className="header">
        <h1>Nirikshan — Label Compliance Inspector</h1>
        <div className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
          {status}
        </div>
      </header>

      {/* Context Config Form */}
      <div className="card context-card">
        <h3>Inspection Package Context</h3>
        <form onSubmit={handleScan} className="context-form">
          <div className="form-grid">
            <div className="form-group">
              <label>Package Type</label>
              <select value={packageType} onChange={(e) => setPackageType(e.target.value)}>
                <option value="retail">Retail Package</option>
                <option value="wholesale">Wholesale Package</option>
                <option value="multi_piece">Multi-Piece Package</option>
                <option value="combination">Combination Package</option>
                <option value="export">Export Package</option>
                <option value="not_for_retail">Not for Retail Sale</option>
              </select>
            </div>

            <div className="form-group">
              <label>Commodity Category</label>
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="general">General Packaged Goods</option>
                <option value="food">Food &amp; Beverages (FSSAI)</option>
                <option value="cosmetic">Cosmetics &amp; Personal Care</option>
                <option value="drug">Drugs &amp; Pharmaceuticals (DPCO)</option>
                <option value="seed">Certified Seeds</option>
                <option value="alcohol">Alcoholic Beverages</option>
                <option value="lpg">LPG Cylinder</option>
                <option value="bidi_incense">Bidi / Incense Sticks</option>
                <option value="electronics">Electronics &amp; Spares</option>
                <option value="textile">Textiles &amp; Garments</option>
                <option value="sheets">Bed Sheets / Woven Materials</option>
                <option value="container">Container Commodities</option>
              </select>
            </div>

            <div className="form-group checkbox-group">
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={isImport}
                  onChange={(e) => setIsImport(e.target.checked)}
                />
                Imported Commodity
              </label>
            </div>
          </div>

          <div className="upload-section">
            <input
              type="file"
              accept="image/*"
              capture="environment"
              onChange={handleFileChange}
              id="file-upload"
              className="file-input"
            />
            <label htmlFor="file-upload" className="file-label">
              {file ? file.name : 'Choose label photo or take picture'}
            </label>
            <button type="submit" disabled={!file || loading} className="btn-primary">
              {loading ? 'Analyzing Label...' : 'Run Compliance Scan'}
            </button>
          </div>
        </form>
      </div>

      {errorMsg && <div className="error-badge">{errorMsg}</div>}

      {scanResult && (
        <div className="results-container">
          {/* Summary Banner */}
          <div className={`summary-banner status-${scanResult.summary.status.toLowerCase().replace(/\s+/g, '-')}`}>
            <div className="summary-status">
              <h2>Status: {scanResult.summary.status}</h2>
              <p className="version-info">Rules Version: {scanResult.rules_version}</p>
            </div>
            <div className="summary-counts">
              <span className="count-badge count-pass">PASS: {scanResult.summary.counts.PASS || 0}</span>
              <span className="count-badge count-fail">FAIL: {scanResult.summary.counts.FAIL || 0}</span>
              <span className="count-badge count-review">REVIEW: {scanResult.summary.counts.NEEDS_REVIEW || 0}</span>
              <span className="count-badge count-na">N/A: {scanResult.summary.counts['N/A'] || 0}</span>
            </div>
          </div>

          {/* Evidence Canvas Overlay */}
          {imageSrc && (
            <div className="card overlay-card">
              <div className="card-header">
                <h3>Evidence Overlay</h3>
                <button type="button" onClick={downloadCanvasImage} className="btn-secondary">
                  Download Evidence PNG
                </button>
              </div>
              <div className="canvas-wrapper">
                <canvas ref={canvasRef} className="evidence-canvas" />
              </div>
            </div>
          )}

          {/* Findings Table */}
          <div className="card findings-card">
            <div className="card-header">
              <h3>Rule Compliance Findings</h3>
              <button
                type="button"
                onClick={() => setUseHindi(!useHindi)}
                className="btn-toggle-lang"
              >
                {useHindi ? 'Switch to English' : 'हिंदी में देखें'}
              </button>
            </div>

            <table className="findings-table">
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Reference</th>
                  <th>Verdict</th>
                  <th>Description</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {applicableFindings.map((finding) => {
                  const isSelected = selectedRuleId === finding.rule_id;
                  const isExpanded = expandedRuleId === finding.rule_id;
                  return (
                    <React.Fragment key={finding.rule_id}>
                      <tr
                        className={`finding-row verdict-${finding.verdict.toLowerCase()} ${
                          isSelected ? 'row-selected' : ''
                        }`}
                        onClick={() => setSelectedRuleId(finding.rule_id)}
                      >
                        <td className="rule-id">{finding.rule_id}</td>
                        <td className="rule-ref">{finding.rule_ref}</td>
                        <td>
                          <span className={`badge verdict-badge badge-${finding.verdict.toLowerCase()}`}>
                            {finding.verdict}
                          </span>
                        </td>
                        <td className="rule-msg">
                          {useHindi ? finding.message_hi : finding.message_en}
                        </td>
                        <td>
                          <button
                            type="button"
                            className="btn-expand"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedRuleId(isExpanded ? null : finding.rule_id);
                            }}
                          >
                            {isExpanded ? 'Hide' : 'Details'}
                          </button>
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr className="detail-row">
                          <td colSpan="5">
                            <div className="detail-panel">
                              {finding.extracted !== null && (
                                <p><strong>Extracted:</strong> {String(finding.extracted)}</p>
                              )}
                              {finding.expected && (
                                <p><strong>Expected/Detail:</strong> {finding.expected}</p>
                              )}
                              {finding.fix_hint_en && (
                                <p className="fix-hint">
                                  <strong>How to fix:</strong> {finding.fix_hint_en}
                                </p>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>

            {/* N/A Accordion */}
            {naFindings.length > 0 && (
              <div className="na-accordion-section">
                <button
                  type="button"
                  className="na-accordion-toggle"
                  onClick={() => setShowNaAccordion(!showNaAccordion)}
                >
                  {showNaAccordion
                    ? `Hide Not Applicable Rules (${naFindings.length})`
                    : `Not Applicable (${naFindings.length})`}
                </button>
                {showNaAccordion && (
                  <ul className="na-list">
                    {naFindings.map((finding) => (
                      <li key={finding.rule_id} className="na-item">
                        <strong>{finding.rule_id} ({finding.rule_ref}):</strong>{' '}
                        {finding.message_en}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* Declarations Card */}
          {scanResult.declarations && (
            <div className="card declarations-card">
              <h3>Extracted Declarations</h3>
              <div className="decl-grid">
                {declarationFields.map(({ key, label }) => {
                  const field = scanResult.declarations[key];
                  const hasValue = field && (field.value !== null || field.raw !== null);
                  const displayVal = hasValue ? renderFieldValue(key, field) : null;
                  const conf = field && field.confidence != null ? (field.confidence * 100).toFixed(1) : null;

                  return (
                    <div key={key} className={`decl-item ${hasValue ? 'found' : 'not-found'}`}>
                      <div className="decl-label">{label}</div>
                      {hasValue ? (
                        <div className="decl-content">
                          <div className={`decl-value ${expandedRuleId === key ? '' : 'clamped'}`}>
                            {displayVal}
                          </div>
                          {field.raw && field.raw !== displayVal && (
                            <div className={`decl-raw ${expandedRuleId === key ? '' : 'clamped'}`}>
                              Raw: {field.raw}
                            </div>
                          )}
                          {((displayVal && displayVal.length > 100) || (field.raw && field.raw.length > 50)) && (
                            <button 
                              className="btn-more" 
                              onClick={() => setExpandedRuleId(expandedRuleId === key ? null : key)}
                            >
                              {expandedRuleId === key ? 'Show less' : 'Show more'}
                            </button>
                          )}
                          {conf && <div className="decl-conf">Confidence: {conf}%</div>}
                        </div>
                      ) : (
                        <div className="decl-missing">Not found</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Raw OCR Panel */}
          <div className="card ocr-toggle-section">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowRawOcr(!showRawOcr)}
            >
              {showRawOcr ? 'Hide raw OCR' : 'Show raw OCR'}
            </button>

            {showRawOcr && scanResult.ocr && (
              <div className="ocr-section">
                <h4>Extracted Text (OCR)</h4>
                {scanResult.ocr.full_text ? (
                  <pre className="ocr-text">{scanResult.ocr.full_text}</pre>
                ) : (
                  <p className="no-text">No text detected in image.</p>
                )}

                {scanResult.ocr.lines && scanResult.ocr.lines.length > 0 && (
                  <div className="lines-list">
                    <h4>Detected Lines &amp; Confidence</h4>
                    <ul>
                      {scanResult.ocr.lines.map((line, idx) => (
                        <li key={idx} className="line-item">
                          <span className="line-text">{line.text}</span>
                          <span className="line-confidence">
                            {(line.confidence * 100).toFixed(1)}%
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
