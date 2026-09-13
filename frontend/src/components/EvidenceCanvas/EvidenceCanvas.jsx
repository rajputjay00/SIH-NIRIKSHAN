import React, { useRef, useEffect } from 'react';
import { mapBbox } from '../../utils/bbox';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import styles from './EvidenceCanvas.module.css';

function getCssVar(name, fallback) {
  if (typeof window === 'undefined') return fallback;
  const val = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return val || fallback;
}

export function EvidenceCanvas({
  imageSrc,
  scanResult,
  selectedRuleId = null,
  onSelectRule,
  className = ''
}) {
  const canvasRef = useRef(null);
  const reducedMotion = useReducedMotion();

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

      const passColor = getCssVar('--pass', '#1E9E5A');
      const failColor = getCssVar('--fail', '#D64545');
      const reviewColor = getCssVar('--review', '#E0A100');

      let findings = scanResult.findings || [];

      // Sort findings FAIL first, then NEEDS_REVIEW, then PASS
      const orderMap = { FAIL: 1, NEEDS_REVIEW: 2, PASS: 3 };
      findings = [...findings].sort((a, b) => (orderMap[a.verdict] || 4) - (orderMap[b.verdict] || 4));

      const drawBox = (finding) => {
        if (!finding.evidence_bbox || finding.verdict === 'N/A') return;
        const mappedBox = mapBbox(finding.evidence_bbox, ocrImageSize, drawnSize);
        if (!mappedBox) return;

        const [minX, minY, maxX, maxY] = mappedBox;
        const width = maxX - minX;
        const height = maxY - minY;

        const isSelected = selectedRuleId === finding.rule_id;
        const hasSelection = Boolean(selectedRuleId);

        let strokeColor = passColor;
        let fillColor = 'rgba(30, 158, 90, 0.15)';
        if (finding.verdict === 'FAIL') {
          strokeColor = failColor;
          fillColor = 'rgba(214, 69, 69, 0.2)';
        } else if (finding.verdict === 'NEEDS_REVIEW') {
          strokeColor = reviewColor;
          fillColor = 'rgba(224, 161, 0, 0.2)';
        }

        ctx.globalAlpha = hasSelection && !isSelected ? 0.4 : 1.0;

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

        ctx.globalAlpha = 1.0;
      };

      if (reducedMotion) {
        findings.forEach((f) => drawBox(f));
      } else {
        findings.forEach((f, idx) => {
          setTimeout(() => drawBox(f), idx * 40);
        });
      }
    };
  }, [imageSrc, scanResult, selectedRuleId, reducedMotion]);

  const handleCanvasClick = (e) => {
    if (!scanResult || !canvasRef.current || !onSelectRule) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;

    const clickX = (e.clientX - rect.left) * scaleX;
    const clickY = (e.clientY - rect.top) * scaleY;

    const ocrImageSize = scanResult.ocr?.image_size || { width: canvas.width, height: canvas.height };
    const drawnSize = { width: canvas.width, height: canvas.height };

    const findings = scanResult.findings || [];
    for (const finding of findings) {
      if (!finding.evidence_bbox || finding.verdict === 'N/A') continue;
      const mappedBox = mapBbox(finding.evidence_bbox, ocrImageSize, drawnSize);
      if (!mappedBox) continue;
      const [minX, minY, maxX, maxY] = mappedBox;
      if (clickX >= minX && clickX <= maxX && clickY >= minY && clickY <= maxY) {
        onSelectRule(finding.rule_id);
        return;
      }
    }
  };

  return (
    <div className={`${styles.canvasContainer} ${className}`}>
      <canvas
        ref={canvasRef}
        className={styles.canvasElement}
        onClick={handleCanvasClick}
      />
    </div>
  );
}
