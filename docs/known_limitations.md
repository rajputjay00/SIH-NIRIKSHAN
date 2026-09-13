# Known Limitations

- **Baby Oil Back MRP Detection**: `270(31.351ml)` on the Baby Oil back label is not extracted as MRP due to severe OCR character merging/garbling where price digits are concatenated directly with net content parentheses.
- **Barcode Detection (R33)**: OpenCV `BarcodeDetector` works on unwarped, clean image pixels. On highly curved, reflective, or degraded label surfaces, detection falls back to 8/12/13-digit standalone numeric regex lines in OCR output.
- **Altered MRP / Sticker Detection (R16)**: Sticker detection flags multiple distinct MRP amounts extracted from price lines; if an altered sticker completely obscures the original price so only one price is visible, officer manual inspection is required.
