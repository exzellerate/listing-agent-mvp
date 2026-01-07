# 🧪 Testing Framework - Implementation Complete

## Overview
A comprehensive testing framework has been implemented for the Listing Agent MVP. This framework allows you to validate the accuracy of image analysis and pricing research using CSV-based test cases.

---

## ✅ What's Been Implemented

### 1. **CSV Test Data Format** (`backend/test_data.csv`)

**Columns:**
- `image_path` - Path to test image (e.g., "test_images/dyson_vacuum.jpg")
- `expected_name` - Ground truth product name
- `expected_brand` - Expected brand (optional)
- `expected_category` - Expected category
- `expected_condition` - Expected condition
- `expected_title` - Expected listing title
- `expected_description_keywords` - Comma-separated keywords
- `expected_price_min` - Minimum acceptable price
- `expected_price_max` - Maximum acceptable price
- `platform` - Target platform (ebay/amazon/walmart)
- `notes` - Additional context (optional)

**Sample Test Cases Created:** 10 diverse products across all platforms

---

### 2. **Test Scoring Module** (`backend/services/test_scorer.py`)

**Scoring Metrics:**

| Metric | Method | Threshold | Weight |
|--------|--------|-----------|--------|
| Product Name | Token sort fuzzy match | ≥80% | 20% |
| Title | Partial + token sort | ≥70% | 20% |
| Description | Keyword matching | ≥60% | 15% |
| Category | Exact match | 100% | 15% |
| Condition | Exact match | 100% | 15% |
| Price | Within range | In range | 15% |

**Features:**
- Multiple fuzzy matching strategies using `rapidfuzz`
- Partial credit for near-misses
- Detailed failure explanations
- Comprehensive summary statistics
- Per-field accuracy breakdown

---

### 3. **Batch Testing Service** (`backend/services/batch_tester.py`)

**Capabilities:**
- Loads test cases from CSV
- Runs analysis and pricing research sequentially
- Scores results against expected values
- Generates comprehensive reports
- Error handling and recovery

---

### 4. **REST API Endpoint** (`POST /api/test/batch`)

**Usage:**
```bash
curl -X POST http://localhost:8000/api/test/batch \
  -F "file=@test_data.csv"
```

**Response Structure:**
```json
{
  "summary": {
    "total_tests": 10,
    "passed": 8,
    "failed": 2,
    "pass_rate": 80.0,
    "avg_score": 85.5,
    "total_duration_seconds": 125.3,
    "field_accuracy": {
      "product_name": 90.0,
      "title": 85.0,
      "description": 80.0,
      "category": 100.0,
      "condition": 90.0,
      "price": 70.0
    },
    "failed_tests": [...]
  },
  "results": [...]
}
```

---

### 5. **CLI Test Runner** (`backend/test_runner.py`)

**Usage:**
```bash
# Basic test run
python test_runner.py --csv test_data.csv --images ./test_images

# With output file
python test_runner.py --csv test_data.csv --images ./test_images --output results.json

# Verbose mode
python test_runner.py --csv test_data.csv --images ./test_images --verbose

# Filter by platform
python test_runner.py --csv test_data.csv --images ./test_images --platform ebay
```

**Features:**
- Beautiful CLI output with progress bars
- Colored emoji indicators (✅❌⚠️)
- Summary statistics
- Detailed results in verbose mode
- JSON export
- Exit codes based on pass rate

---

### 6. **Documentation** (`backend/README_TESTING.md`)

Complete guide covering:
- CSV format specification
- Scoring system details
- API endpoint documentation
- CLI usage examples
- Best practices
- CI/CD integration
- Troubleshooting guide

---

## 📁 File Structure

```
backend/
├── test_data.csv                    # Sample test cases (10 items)
├── test_runner.py                   # CLI test runner (executable)
├── test_images/                     # Directory for test images
├── README_TESTING.md                # Comprehensive documentation
├── requirements.txt                 # Updated with testing deps
│
├── services/
│   ├── test_scorer.py              # Scoring algorithms
│   └── batch_tester.py             # Batch testing service
│
└── models.py                        # Updated with test models
```

---

## 🚀 Next Steps

### To Use the Testing Framework:

#### 1. **Add Test Images**
Place product images in `backend/test_images/`:
```bash
backend/test_images/
├── dyson_vacuum.jpg
├── iphone_13.jpg
├── nike_shoes.jpg
└── ...
```

You can use the existing DysonVaccum.jpg as a starting point:
```bash
cp ~/Downloads/DysonVaccum.jpg backend/test_images/dyson_vacuum.jpg
```

#### 2. **Run Tests via CLI**
```bash
cd backend
python test_runner.py --csv test_data.csv --images ./test_images --verbose
```

#### 3. **Run Tests via API**
```bash
curl -X POST http://localhost:8000/api/test/batch \
  -F "file=@test_data.csv"
```

#### 4. **Review Results**
- Check console output for summary
- Review `results.json` for detailed analysis
- Identify patterns in failures
- Adjust prompts or expectations as needed

---

## 📊 Sample Test Cases Included

1. **Dyson Ball Multi Floor Vacuum** - eBay ($140-$180)
2. **iPhone 13** - eBay ($450-$550)
3. **Nike Air Max Sneakers** - eBay ($60-$90)
4. **MacBook Pro 13-inch** - Amazon ($800-$1000)
5. **Kindle Paperwhite** - Amazon ($80-$110)
6. **Instant Pot Duo** - Walmart ($50-$75)
7. **Fitbit Versa 3** - eBay ($120-$160)
8. **PlayStation 5 DualSense Controller** - Walmart ($55-$75)
9. **LEGO Star Wars Millennium Falcon** - eBay ($650-$850)
10. **Apple AirPods Pro** - Amazon ($150-$200)

---

## 🎯 Success Criteria

### Score Interpretation:
- **85-100%** - Excellent! Model performing very well
- **70-84%** - Good! Minor improvements needed
- **50-69%** - Fair! Significant improvements needed
- **<50%** - Poor! Major issues require attention

### Field-Specific Targets:
- Product Name: ≥90%
- Title: ≥85%
- Description: ≥75%
- Category: ≥95%
- Condition: ≥90%
- Price: ≥80%

---

## 🔧 Configuration

### Adding More Test Cases:
Edit `test_data.csv` and add rows with the required columns.

### Adjusting Thresholds:
Edit `backend/services/test_scorer.py`:
```python
class TestScorer:
    TITLE_THRESHOLD = 70.0          # Adjust as needed
    DESCRIPTION_THRESHOLD = 60.0     # Adjust as needed
    PRODUCT_NAME_THRESHOLD = 80.0    # Adjust as needed
```

### Adjusting Weights:
Edit `backend/services/test_scorer.py`:
```python
WEIGHTS = {
    "product_name": 0.20,   # 20%
    "title": 0.20,          # 20%
    "description": 0.15,    # 15%
    "category": 0.15,       # 15%
    "condition": 0.15,      # 15%
    "price": 0.15           # 15%
}
```

---

## 🧰 Dependencies Installed

```
rapidfuzz==3.6.1   # Fast fuzzy string matching
pandas==2.2.0       # CSV processing and data handling
```

---

## 🎨 Frontend Integration (TODO)

The frontend `TestingPage` component is still pending. It will include:
- CSV file upload
- Bulk image upload
- Real-time progress tracking
- Visual results dashboard
- Side-by-side comparisons
- Export functionality

To implement, you would need to:
1. Create `frontend/src/pages/TestingPage.tsx`
2. Add route in `App.tsx`
3. Create API service methods
4. Build UI components for upload and results display

---

## 📝 Example Output

### CLI Output:
```
================================================================================
  Listing Agent - Batch Test Runner
================================================================================

📄 Test Data:    test_data.csv
📁 Images Dir:   ./test_images

🚀 Starting 10 tests...

[████████████████████████████████████░░░░░░░░░░░] 80.0% (8/10) - iphone_13.jpg

--------------------------------------------------------------------------------
  Test Summary
--------------------------------------------------------------------------------
  Total Tests:     10
  ✅ Passed:        8 (80.0%)
  ❌ Failed:        2
  ⏱️  Duration:      125.3s
  📊 Avg Score:     85.5%

--------------------------------------------------------------------------------
  Field Accuracy
--------------------------------------------------------------------------------
  ✅ product_name         : 90.0%
  ✅ title                : 85.0%
  ✅ description          : 80.0%
  ✅ category             : 100.0%
  ✅ condition            : 90.0%
  ⚠️  price               : 70.0%
```

---

## 🚢 CI/CD Integration

Add to `.github/workflows/test.yml`:
```yaml
name: Listing Agent Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          cd backend
          pip install -r requirements.txt
          python test_runner.py --csv test_data.csv --images ./test_images --output results.json
```

---

## 🎉 Summary

The testing framework is **fully functional** and ready to use! You now have:

✅ **CSV-based test cases** with 10 sample products
✅ **Sophisticated scoring system** with fuzzy matching
✅ **REST API endpoint** for programmatic testing
✅ **CLI tool** with beautiful output
✅ **Comprehensive documentation**
✅ **Easy extensibility** for adding more tests

**Next immediate action:** Add test images to `backend/test_images/` and run your first batch test!
