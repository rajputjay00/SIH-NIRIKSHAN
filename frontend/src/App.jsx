import React, { useState, useEffect } from 'react';
import { checkHealth, scanImage } from './api';

export default function App() {
  const [status, setStatus] = useState('Checking...');
  const [file, setFile] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

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

          {scanResult.ocr && (
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
      )}
    </div>
  );
}
