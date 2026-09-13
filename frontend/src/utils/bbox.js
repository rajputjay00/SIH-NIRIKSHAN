/**
 * Maps a bounding box from the original OCR image dimensions to the dimensions of the canvas element.
 * 
 * @param {Array} bbox - The bounding box from the API. Can be [[x1, y1], [x2, y2], ...] or [minX, minY, maxX, maxY].
 * @param {Object} imageSize - {width, height} of the processed OCR image.
 * @param {Object} drawnSize - {width, height} of the drawn canvas or image element.
 * @returns {Array} - The mapped bounding box in [minX, minY, maxX, maxY] format.
 */
export function mapBbox(bbox, imageSize, drawnSize) {
    if (!bbox || !imageSize || !drawnSize) return null;

    let minX, minY, maxX, maxY;
    if (bbox.length === 4 && Array.isArray(bbox[0])) {
        minX = Math.min(...bbox.map(p => p[0]));
        minY = Math.min(...bbox.map(p => p[1]));
        maxX = Math.max(...bbox.map(p => p[0]));
        maxY = Math.max(...bbox.map(p => p[1]));
    } else if (bbox.length === 4) {
        [minX, minY, maxX, maxY] = bbox;
    } else {
        return null;
    }

    const scaleX = drawnSize.width / imageSize.width;
    const scaleY = drawnSize.height / imageSize.height;

    return [
        minX * scaleX,
        minY * scaleY,
        maxX * scaleX,
        maxY * scaleY
    ];
}
