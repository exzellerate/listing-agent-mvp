# Testing Framework Documentation

## Overview
This testing framework allows you to validate the accuracy of the Listing Agent's image analysis and pricing research capabilities using a CSV-based test dataset.

## CSV Format Specification

### Column Definitions

| Column | Type | Required | Description |
|--------|------|----------|-------------|
| `image_path` | string | Yes | Relative path to test image from backend directory (e.g., "test_images/iphone.jpg") |
| `expected_name` | string | Yes | Ground truth product name for comparison |
| `expected_brand` | string | No | Expected brand name (can be empty) |
| `expected_category` | string | Yes | Expected product category |
| `expected_condition` | string | Yes | Expected condition (New, Used - Like New, Used - Good, Used - Fair, Refurbished) |
| `expected_title` | string | Yes | Expected listing title for similarity comparison |
| `expected_description_keywords` | string | Yes | Comma-separated keywords that should appear in description |
| `expected_price_min` | float | Yes | Minimum acceptable price in USD |
| `expected_price_max` | float | Yes | Maximum acceptable price in USD |
| `platform` | string | Yes | Target platform: ebay, amazon, or walmart |
| `notes` | string | No | Additional context or special considerations |

### Example CSV Row

```csv
image_path,expected_name,expected_brand,expected_category,expected_condition,expected_title,expected_description_keywords,expected_price_min,expected_price_max,platform,notes
test_images/iphone_13.jpg,iPhone 13,Apple,Cell Phones & Smartphones,Used - Like New,Apple iPhone 13 128GB Unlocked,"A15 bionic,5G,dual camera,iOS,unlocked",450.00,550.00,ebay,Excellent condition with minimal wear
```

## Scoring System

### Title Similarity (0-100%)
- Uses fuzzy string matching (Levenshtein distance)
- Compares generated title with expected title
- **Pass threshold**: ≥70%

### Description Quality (0-100%)
- Keyword matching against expected_description_keywords
- Calculates percentage of keywords found
- **Pass threshold**: ≥60%

### Product Name Similarity (0-100%)
- Fuzzy match between detected and expected product name
- **Pass threshold**: ≥80%

### Category Match
- Exact match (case-insensitive)
- **Pass threshold**: Exact match

### Condition Match
- Exact match
- **Pass threshold**: Exact match

### Price Accuracy
- Checks if suggested price falls within expected_price_min and expected_price_max
- **Pass threshold**: Within range

### Overall Score
- Weighted average of all metrics:
  - Product Name: 20%
  - Title: 20%
  - Description: 15%
  - Category: 15%
  - Condition: 15%
  - Price: 15%

## API Endpoints

### POST /api/test/batch
Upload a CSV test file and optional images to run batch tests.

**Request:**
- Content-Type: `multipart/form-data`
- Form fields:
  - `file`: CSV file containing test cases
  - `images`: (optional) ZIP file or multiple image files

**Response:**
```json
{
  "summary": {
    "total_tests": 10,
    "passed": 8,
    "failed": 2,
    "pass_rate": 80.0,
    "avg_score": 85.5,
    "total_duration_seconds": 125.3
  },
  "field_accuracy": {
    "product_name": 90.0,
    "title": 85.0,
    "description": 80.0,
    "category": 100.0,
    "condition": 90.0,
    "price": 70.0
  },
  "results": [
    {
      "test_id": 1,
      "image_path": "test_images/iphone_13.jpg",
      "status": "passed",
      "overall_score": 87.5,
      "duration_seconds": 12.5,
      "analysis": {
        "product_name": {
          "expected": "iPhone 13",
          "actual": "Apple iPhone 13",
          "score": 95.0,
          "passed": true
        },
        "title": {
          "expected": "Apple iPhone 13 128GB Unlocked",
          "actual": "Apple iPhone 13 128GB - Unlocked Smartphone",
          "score": 92.0,
          "passed": true
        },
        "description": {
          "expected_keywords": ["A15 bionic", "5G", "dual camera", "iOS", "unlocked"],
          "found_keywords": ["A15 bionic", "5G", "dual camera", "unlocked"],
          "score": 80.0,
          "passed": true
        },
        "category": {
          "expected": "Cell Phones & Smartphones",
          "actual": "Cell Phones & Smartphones",
          "passed": true
        },
        "condition": {
          "expected": "Used - Like New",
          "actual": "Used - Like New",
          "passed": true
        },
        "price": {
          "expected_range": [450.0, 550.0],
          "actual": 485.99,
          "passed": true
        }
      }
    }
  ],
  "failed_tests": [
    {
      "test_id": 5,
      "image_path": "test_images/watch.jpg",
      "reason": "Price out of range (expected: 120-160, actual: 189.99)",
      "overall_score": 65.0
    }
  ]
}
```

### GET /api/test/results/{test_run_id}
Retrieve results from a previous test run.

## CLI Usage

### Basic Test Run
```bash
python test_runner.py --csv test_data.csv --images ./test_images
```

### With Output File
```bash
python test_runner.py --csv test_data.csv --images ./test_images --output results.json
```

### Verbose Mode
```bash
python test_runner.py --csv test_data.csv --images ./test_images --verbose
```

### Filter by Platform
```bash
python test_runner.py --csv test_data.csv --images ./test_images --platform ebay
```

## Frontend Testing Interface

Access the testing interface at: `http://localhost:5173/testing`

### Features:
1. **CSV Upload**: Upload your test_data.csv file
2. **Image Upload**: Bulk upload test images (supports drag & drop)
3. **Progress Tracking**: Real-time progress bar
4. **Results Dashboard**: Visual summary with charts
5. **Detailed View**: Side-by-side comparison for each test
6. **Export**: Download results as JSON or CSV

## Creating Test Images

### Directory Structure
```
backend/
├── test_images/
│   ├── iphone_13.jpg
│   ├── dyson_vacuum.jpg
│   ├── nike_shoes.jpg
│   └── ...
├── test_data.csv
└── test_runner.py
```

### Image Requirements
- Format: JPEG, PNG, WebP, or GIF
- Max size: 10MB per image
- Resolution: At least 640x480 recommended
- Clear, well-lit product photos work best

## Best Practices

1. **Diverse Test Set**: Include various product types, conditions, and platforms
2. **Realistic Expectations**: Set expected values based on actual marketplace standards
3. **Keyword Selection**: Choose 5-10 key descriptive terms for description matching
4. **Price Ranges**: Use realistic price ranges with ±20% tolerance
5. **Regular Testing**: Run tests after any model or prompt changes
6. **Version Control**: Keep test_data.csv in git to track accuracy over time

## Interpreting Results

### High Score (85-100%)
- Excellent accuracy
- Model is performing well
- Minor refinements needed

### Medium Score (70-84%)
- Good accuracy
- Some improvements needed
- Review failed cases for patterns

### Low Score (<70%)
- Significant issues
- Prompt engineering needed
- Check for systematic errors

## Troubleshooting

### Test Fails: Image Not Found
- Ensure image_path is relative to backend directory
- Check file exists and has correct permissions

### Low Title Similarity
- Review platform-specific title requirements
- Adjust expected_title to match typical format

### Low Description Score
- Ensure keywords are specific and realistic
- Avoid overly generic terms

### Price Out of Range
- Verify expected_price_min/max are reasonable
- Market prices may fluctuate

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Listing Agent Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          cd backend
          python test_runner.py --csv test_data.csv --images ./test_images --output results.json
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: test-results
          path: backend/results.json
```

## Future Enhancements

- [ ] Semantic similarity using sentence transformers
- [ ] A/B testing between different prompts
- [ ] Historical tracking of accuracy over time
- [ ] Automated regression detection
- [ ] Performance benchmarking
- [ ] Multi-language support testing
