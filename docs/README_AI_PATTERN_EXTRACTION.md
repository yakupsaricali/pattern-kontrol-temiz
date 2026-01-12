# AI Pattern Extraction - Google Gemini

This script uses Google Gemini AI to analyze rug images and extract pattern information.

## Setup

1. **Install required packages:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get your Google Gemini API key:**
   - Go to https://makersuite.google.com/app/apikey
   - Create a new API key
   - Copy the API key

3. **Set the API key as an environment variable:**
   - Windows PowerShell:
     ```powershell
     $env:GEMINI_API_KEY="your_api_key_here"
     ```
   - Windows CMD:
     ```cmd
     set GEMINI_API_KEY=your_api_key_here
     ```
   - Linux/Mac:
     ```bash
     export GEMINI_API_KEY=your_api_key_here
     ```

## Usage

### Test Run (Small Sample)
```bash
python test_ai_pattern_extraction.py
```

This will:
- Analyze 10 rug images (configurable via `TEST_SAMPLE_SIZE`)
- Extract pattern information using Gemini AI
- Save results to `test_ai_pattern_results.csv`
- Display summary statistics

### Full Run
After testing, you can modify the script to process all images by changing `TEST_SAMPLE_SIZE` to a larger number or removing the limit.

## Output

The script creates a CSV file with:
- Variant SKU
- Product SKU
- Original Patterns (empty for these rugs)
- AI Detected Pattern (the pattern extracted by Gemini)
- Design Image URL

## Notes

- The script includes a 1-second delay between API calls to avoid rate limiting
- If an image fails to analyze, it will be marked as "Error"
- Make sure you have sufficient API quota for the number of images you want to analyze

