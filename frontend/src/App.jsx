import React, { useState, useEffect } from 'react';
import { checkHealth, scanImage } from './api';

export default function App() {
  const [status, setStatus] = useState('Checking...');
  const [file, setFile] = useState(null);
  const [scanResult, setScanResult] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkHealth()
      .then(() => setStatus('Backend online'))
      .catch(() => setStatus('Backend offline'));
  }, []);

  const handleScan = async (e) => {
    e.preventDefault();
    if (!file) return;
    setLoading(true);
    try {
      const data = await scanImage(file);
      setScanResult(data);
    } catch (err) {
      alert('Error scanning label');
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

      {scanResult && (
        <div className="result-card">
          <h3>Scan Results</h3>
          <p><strong>Filename:</strong> {scanResult.filename}</p>
          <p><strong>Width:</strong> {scanResult.width} px</p>
          <p><strong>Height:</strong> {scanResult.height} px</p>
        </div>
      )}
    </div>
  );
}
