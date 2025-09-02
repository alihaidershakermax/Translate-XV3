# Fonts Directory

This directory should contain the following fonts for proper PDF generation:

1. **Noto Sans Arabic** - For Arabic text support
   - NotoSansArabic-Regular.ttf
   - NotoSansArabic-Bold.ttf

2. **Liberation Sans** - Fallback font
   - LiberationSans-Regular.ttf
   - LiberationSans-Bold.ttf

3. **DejaVu Sans** - Additional fallback font
   - DejaVuSans.ttf
   - DejaVuSans-Bold.ttf

These fonts are used by the document generator to properly render Arabic text in PDF documents. The system will automatically try to register these fonts in the order listed above.

If these fonts are not available, the system will fall back to Helvetica, which may not properly display Arabic characters.