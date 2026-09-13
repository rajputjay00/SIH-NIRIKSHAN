import { mapBbox } from './bbox.js';
import assert from 'assert';

function runTests() {
    console.log("Running bbox mapping tests...");

    // Test: Bottom-right corner maps to bottom-right corner
    // Suppose original image is 1000x1000.
    // The processed image (ocr.image_size) is 500x500.
    // The drawn size in canvas is 250x250.
    // Bottom right corner in processed image: [400, 400, 500, 500]
    // Expected mapped bbox in canvas: [200, 200, 250, 250]
    const bbox = [400, 400, 500, 500];
    const imageSize = { width: 500, height: 500 };
    const drawnSize = { width: 250, height: 250 };
    
    const mapped = mapBbox(bbox, imageSize, drawnSize);
    assert.deepStrictEqual(mapped, [200, 200, 250, 250], "Bottom right corner mapping failed.");

    // Test with array of points format [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
    const bboxPts = [[400, 400], [500, 400], [500, 500], [400, 500]];
    const mappedPts = mapBbox(bboxPts, imageSize, drawnSize);
    assert.deepStrictEqual(mappedPts, [200, 200, 250, 250], "Bottom right corner mapping with points failed.");

    console.log("All bbox tests passed!");
}

runTests();
