import React, { useState, useEffect } from 'react';
import { checkHealth, scanImage } from './api';

export default function App() {
  const [status, setStatus] = useState('Checking...');
  const [file, setFile] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [showRawOcr, setShowRawOcr] = useState(false);

  useEffect(() => {
    checkHealth()
      .then(() => setStatus('Backend online'))
      .catch(() => setStatus('Backend offline'));
  }, []);

  const handleScan = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const data = await scanImage(file);
      setScanResult(data);
    } catch (err) {
      setErrorMsg('Error scanning label. Ensure format is JPEG/PNG/WebP and under 10 MB.');
    } finally {
      setLoading(false);
    }
  };

  const isOnline = status === 'Backend online';

  const renderFieldValue = (key, field) => {
    if (!field) return null;
    if (key === 'net_quantity') {
      let str = `${field.value ?? ''} ${field.unit ?? ''}`.strip() || field.raw;
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

  return (
    <div className="container">
      <h1>Label Check</h1>
      <div className={`status-badge ${isOnline ? 'online' : 'offline'}`}>
        {status}
      </div>

      <form onSubmit={handleScan}>
        <div className="form-group">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={(e) => setFile(e.target.files[0])}
          />
        </div>
        <button type="submit" disabled={!file || loading}>
          {loading ? 'Scanning...' : 'Scan label'}
        </button>
      </form>

      {errorMsg && <div className="error-badge">{errorMsg}</div>}

      {scanResult && (
        <div className="result-card">
          <h3>Scan Results</h3>
          <p><strong>Filename:</strong> {scanResult.filename}</p>
          <p><strong>Dimensions:</strong> {scanResult.width} × {scanResult.height} px</p>

          {scanResult.declarations && (
            <div className="declarations-card">
              <h4>Extracted Declarations</h4>
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
                          <div className="decl-value">{displayVal}</div>
                          {field.raw && field.raw !== displayVal && (
                            <div className="decl-raw">Raw: {field.raw}</div>
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

          <div className="ocr-toggle-section">
            <button
              type="button"
              className="toggle-btn"
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
