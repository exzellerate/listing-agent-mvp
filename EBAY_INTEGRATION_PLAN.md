# eBay Integration Plan - Listing Agent MVP

## Overview
Integrate eBay API to allow users to post listings directly from the Listing Agent interface, with comprehensive failure handling and retry mechanisms.

---

## Architecture Overview

```
┌─────────────────┐
│   Frontend UI   │
│  - Preview      │
│  - Auth Flow    │
│  - Post Button  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│      Backend FastAPI            │
│  ┌──────────────────────────┐   │
│  │  eBay OAuth Service      │   │
│  │  - Token Management      │   │
│  │  - Refresh Logic         │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  eBay Listing Service    │   │
│  │  - Create Inventory      │   │
│  │  - Create Offer          │   │
│  │  - Publish Listing       │   │
│  │  - Image Upload          │   │
│  └──────────────────────────┘   │
│  ┌──────────────────────────┐   │
│  │  Failure Handler         │   │
│  │  - Retry Queue           │   │
│  │  - Error Tracking        │   │
│  │  - Notifications         │   │
│  └──────────────────────────┘   │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────┐
│   Database      │
│  - OAuth Tokens │
│  - Listings     │
│  - Failures     │
└─────────────────┘
```

---

## Phase 1: Database Schema Extensions

### New Tables

#### 1. `ebay_credentials`
Stores user OAuth tokens and credentials.

```sql
CREATE TABLE ebay_credentials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(100) UNIQUE,  -- For future multi-user support
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_expires_at DATETIME NOT NULL,
    scope TEXT,  -- OAuth scopes granted
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. `ebay_listings`
Tracks all eBay listing attempts and states.

```sql
CREATE TABLE ebay_listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,  -- Links to product_analyses

    -- eBay Identifiers
    sku VARCHAR(100) UNIQUE,  -- Seller-defined SKU
    listing_id VARCHAR(100),  -- eBay listing ID
    offer_id VARCHAR(100),  -- eBay offer ID

    -- Listing Data
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER DEFAULT 1,
    condition VARCHAR(50),  -- NEW, USED_EXCELLENT, etc.
    category_id VARCHAR(50),

    -- Status Tracking
    status VARCHAR(50) NOT NULL,  -- draft, creating, published, failed, cancelled
    ebay_status VARCHAR(50),  -- eBay's status

    -- Images
    image_urls TEXT,  -- JSON array of uploaded image URLs

    -- Failure Handling
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    last_error_code VARCHAR(50),
    last_retry_at DATETIME,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME,

    FOREIGN KEY (analysis_id) REFERENCES product_analyses(id)
);
```

#### 3. `ebay_listing_failures`
Detailed failure tracking for debugging and analytics.

```sql
CREATE TABLE ebay_listing_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    listing_id INTEGER NOT NULL,

    -- Failure Details
    failure_stage VARCHAR(50),  -- auth, inventory, offer, publish, image_upload
    error_code VARCHAR(100),
    error_message TEXT,
    error_details TEXT,  -- JSON with full error response

    -- Recovery
    is_recoverable BOOLEAN DEFAULT TRUE,
    recovery_suggestion TEXT,

    -- Timestamps
    occurred_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (listing_id) REFERENCES ebay_listings(id)
);
```

---

## Phase 2: Backend Implementation

### File Structure

```
backend/
├── services/
│   ├── ebay/
│   │   ├── __init__.py
│   │   ├── oauth.py           # OAuth flow management
│   │   ├── inventory.py       # Inventory API calls
│   │   ├── listing.py         # Listing creation orchestrator
│   │   └── image_upload.py    # eBay image upload
│   └── failure_handler.py     # Retry and failure management
├── database_models.py         # Add new models
├── models.py                  # Pydantic models for API
└── main.py                    # New endpoints
```

### Key Components

#### 1. OAuth Service (`services/ebay/oauth.py`)

**Purpose**: Manage eBay OAuth 2.0 flow and token lifecycle.

**Key Functions**:
- `get_authorization_url()` - Generate OAuth consent URL
- `exchange_code_for_token(code)` - Exchange auth code for tokens
- `refresh_access_token()` - Auto-refresh expired tokens
- `get_valid_token()` - Get current valid token (auto-refresh if needed)

**Implementation Notes**:
- Use official eBay OAuth library: `ebay-oauth-python-client`
- Store tokens encrypted in database
- Implement token expiry checking (tokens expire in ~2 hours)
- Auto-refresh 5 minutes before expiry
- Handle refresh token rotation

#### 2. Inventory Service (`services/ebay/inventory.py`)

**Purpose**: Create and manage eBay inventory items.

**Key Functions**:
- `create_inventory_item(sku, product_data)` - Create/update inventory
- `get_inventory_item(sku)` - Retrieve inventory item
- `delete_inventory_item(sku)` - Remove inventory

**eBay API Endpoint**: `PUT /sell/inventory/v1/inventory_item/{sku}`

**Required Data**:
```json
{
  "availability": {
    "shipToLocationAvailability": {
      "quantity": 1
    }
  },
  "condition": "USED_EXCELLENT",
  "product": {
    "title": "Product Title",
    "description": "Product Description",
    "aspects": {
      "Brand": ["Nike"],
      "Model": ["Air Max"]
    },
    "imageUrls": ["https://..."]
  }
}
```

#### 3. Listing Service (`services/ebay/listing.py`)

**Purpose**: Orchestrate the complete listing creation process.

**Key Functions**:
- `create_listing(analysis_id, listing_data)` - Main orchestrator
- `publish_listing(listing_id)` - Publish to eBay
- `update_listing_status(listing_id, status, error)` - Status tracking
- `retry_failed_listing(listing_id)` - Retry logic

**Workflow**:
```
1. Validate data
2. Generate unique SKU
3. Upload images to eBay
4. Create inventory item
5. Create offer with pricing
6. Publish offer
7. Track status
8. Handle failures at each step
```

#### 4. Image Upload Service (`services/ebay/image_upload.py`)

**Purpose**: Upload product images to eBay's EPS (eBay Picture Services).

**eBay API Endpoint**: `POST /sell/inventory/v1/inventory_item/{sku}/image`

**Key Functions**:
- `upload_image(sku, image_data, image_index)` - Upload single image
- `upload_multiple_images(sku, images)` - Batch upload
- `delete_image(sku, image_url)` - Remove image

**Implementation Notes**:
- eBay accepts images up to 12MB
- Formats: JPEG, PNG, GIF, BMP, TIFF
- Maximum 12 images per listing
- Images must be at least 500x500 pixels
- First image becomes primary listing image

#### 5. Failure Handler (`services/failure_handler.py`)

**Purpose**: Comprehensive failure tracking and retry mechanism.

**Key Functions**:
- `log_failure(listing_id, stage, error)` - Record failure
- `should_retry(listing_id)` - Check retry eligibility
- `schedule_retry(listing_id, delay)` - Queue for retry
- `get_recovery_suggestion(error_code)` - Provide user guidance

**Retry Strategy**:
- Exponential backoff: 1min, 5min, 15min, 1hour
- Max 3 retries for transient errors
- No retry for permanent errors (invalid data, auth issues)
- Manual retry option for all failures

**Error Categories**:
```python
TRANSIENT_ERRORS = [
    'RATE_LIMIT_EXCEEDED',
    'SERVICE_UNAVAILABLE',
    'TIMEOUT',
    'NETWORK_ERROR'
]

PERMANENT_ERRORS = [
    'INVALID_TOKEN',
    'INVALID_DATA',
    'DUPLICATE_SKU',
    'INVALID_CATEGORY'
]

RECOVERABLE_ERRORS = [
    'IMAGE_TOO_LARGE',
    'INVALID_IMAGE_FORMAT',
    'MISSING_REQUIRED_FIELD'
]
```

---

## Phase 3: API Endpoints

### 1. OAuth Endpoints

#### `GET /api/ebay/auth/url`
Get eBay OAuth authorization URL.

**Response**:
```json
{
  "authorization_url": "https://auth.ebay.com/oauth2/authorize?...",
  "state": "random_state_token"
}
```

#### `POST /api/ebay/auth/callback`
Handle OAuth callback with authorization code.

**Request**:
```json
{
  "code": "v^1.1#i^1#...",
  "state": "random_state_token"
}
```

**Response**:
```json
{
  "success": true,
  "expires_at": "2025-10-14T15:30:00Z"
}
```

#### `GET /api/ebay/auth/status`
Check if user has valid eBay credentials.

**Response**:
```json
{
  "authenticated": true,
  "expires_at": "2025-10-14T15:30:00Z",
  "scopes": ["https://api.ebay.com/oauth/api_scope/sell.inventory"]
}
```

#### `DELETE /api/ebay/auth/revoke`
Revoke eBay access and delete credentials.

### 2. Listing Endpoints

#### `POST /api/ebay/listings/create`
Create a new eBay listing.

**Request**:
```json
{
  "analysis_id": 123,
  "title": "Nike Air Max 90 Men's Shoes Size 10",
  "description": "...",
  "price": 89.99,
  "quantity": 1,
  "condition": "USED_EXCELLENT",
  "category_id": "15709",
  "images": ["base64_image_1", "base64_image_2"],
  "shipping_policy_id": "...",
  "return_policy_id": "...",
  "payment_policy_id": "..."
}
```

**Response**:
```json
{
  "success": true,
  "listing_id": 456,
  "sku": "LA-2025-001",
  "status": "creating",
  "estimated_completion": "2025-10-14T14:30:00Z"
}
```

**Failure Response**:
```json
{
  "success": false,
  "error": "INVALID_CATEGORY",
  "message": "Category ID is not valid for this product type",
  "details": {...},
  "recoverable": true,
  "suggestion": "Please select a valid category for this item"
}
```

#### `GET /api/ebay/listings/{listing_id}`
Get listing status and details.

**Response**:
```json
{
  "id": 456,
  "sku": "LA-2025-001",
  "status": "published",
  "ebay_listing_id": "v1|1234567890|0",
  "ebay_url": "https://www.ebay.com/itm/1234567890",
  "published_at": "2025-10-14T14:30:00Z",
  "retry_count": 0,
  "last_error": null
}
```

#### `POST /api/ebay/listings/{listing_id}/retry`
Manually retry a failed listing.

#### `DELETE /api/ebay/listings/{listing_id}`
Cancel/delete a listing.

#### `GET /api/ebay/listings`
List all listings with filtering.

**Query Params**: `?status=failed&limit=10&offset=0`

### 3. Utility Endpoints

#### `GET /api/ebay/categories/suggest`
Get category suggestions based on product name.

**Query Params**: `?product_name=Nike+Shoes`

**Response**:
```json
{
  "suggestions": [
    {
      "category_id": "15709",
      "category_name": "Men's Shoes",
      "category_path": "Clothing, Shoes & Accessories > Men > Men's Shoes",
      "confidence": 0.95
    }
  ]
}
```

#### `GET /api/ebay/policies`
Get user's business policies (shipping, return, payment).

---

## Phase 4: Frontend Implementation

### Components to Create

#### 1. `EbayAuthButton.tsx`
OAuth authentication flow.

**States**:
- Not connected
- Authenticating
- Connected
- Error

**Features**:
- Open OAuth popup window
- Handle callback
- Show connection status
- Revoke access button

#### 2. `ListingPreview.tsx`
Preview listing before posting to eBay.

**Features**:
- Show formatted title, description, price
- Image gallery preview
- Edit fields before posting
- Category selector
- Condition selector
- Shipping/return policy selectors

#### 3. `PostToEbayButton.tsx`
Post listing action with status tracking.

**States**:
- Ready to post
- Uploading images
- Creating inventory
- Creating offer
- Publishing
- Success
- Failed

**Features**:
- Progress indicator
- Cancel action
- Retry on failure
- View on eBay link when published

#### 4. `ListingStatusIndicator.tsx`
Show real-time listing status.

**Features**:
- Status badge (draft, creating, published, failed)
- Retry button for failures
- Error details
- Recovery suggestions

#### 5. `EbayListingsTable.tsx`
Dashboard of all eBay listings.

**Features**:
- List all listings
- Filter by status
- Retry failed listings
- View eBay listing link
- Delete listings

---

## Phase 5: Failure States & Error Handling

### Failure Categories

#### 1. Authentication Failures
- **Cause**: Expired/invalid OAuth tokens
- **Recovery**: Auto-refresh token, or prompt re-authentication
- **User Action**: Re-authorize eBay access

#### 2. Validation Failures
- **Cause**: Invalid data (price, category, title length, etc.)
- **Recovery**: Show specific validation errors
- **User Action**: Fix data and retry

#### 3. Image Upload Failures
- **Cause**: File too large, invalid format, network error
- **Recovery**: Resize/convert image, retry upload
- **User Action**: Provide different image or retry

#### 4. Category Mismatch
- **Cause**: AI suggested category not valid on eBay
- **Recovery**: Suggest alternative categories
- **User Action**: Select correct category

#### 5. Rate Limiting
- **Cause**: Too many API requests
- **Recovery**: Exponential backoff, queue requests
- **User Action**: Wait and auto-retry

#### 6. Duplicate SKU
- **Cause**: SKU already exists
- **Recovery**: Generate new SKU
- **User Action**: Automatic - no action needed

#### 7. Policy Violations
- **Cause**: Product violates eBay policies
- **Recovery**: None - permanent failure
- **User Action**: Don't list this item, or modify description

#### 8. Network/Service Errors
- **Cause**: eBay API downtime, network issues
- **Recovery**: Retry with exponential backoff
- **User Action**: Wait for auto-retry or manual retry

### Error Handling Flow

```
┌─────────────────┐
│  Create Listing │
└────────┬────────┘
         │
         ▼
    ┌────────┐
    │ Validate│
    └────┬───┘
         │ Error
         ├──────────► Log Error ──► Show User ──► Allow Fix ──► Retry
         │ OK
         ▼
    ┌─────────┐
    │Upload   │
    │Images   │
    └────┬────┘
         │ Error
         ├──────────► Log Error ──► Retry (3x) ──► Show User
         │ OK
         ▼
    ┌──────────┐
    │Create    │
    │Inventory │
    └────┬─────┘
         │ Error
         ├──────────► Log Error ──► Check Transient ──► Queue Retry
         │ OK
         ▼
    ┌──────────┐
    │Create    │
    │Offer     │
    └────┬─────┘
         │ Error
         ├──────────► Log Error ──► Rollback Inventory ──► Notify User
         │ OK
         ▼
    ┌──────────┐
    │Publish   │
    └────┬─────┘
         │ Error
         ├──────────► Log Error ──► Keep Draft ──► Allow Manual Publish
         │ OK
         ▼
    ┌──────────┐
    │ SUCCESS! │
    │Show Link │
    └──────────┘
```

---

## Phase 6: Testing Strategy

### Unit Tests
- OAuth token refresh logic
- SKU generation
- Error classification
- Retry eligibility

### Integration Tests
- Complete listing creation flow (sandbox)
- Failure recovery scenarios
- Token expiration handling

### End-to-End Tests
- User authenticates with eBay
- Creates listing from analysis
- Handles failure and retries
- Views published listing on eBay

### Sandbox Testing
Use eBay Sandbox environment for testing:
- Sandbox API URL: `https://api.sandbox.ebay.com`
- Separate sandbox credentials
- Test all failure scenarios safely

---

## Environment Variables

Add to `.env`:

```bash
# eBay API Configuration
EBAY_ENV=SANDBOX  # or PRODUCTION
EBAY_CLIENT_ID=your_client_id
EBAY_CLIENT_SECRET=your_client_secret
EBAY_REDIRECT_URI=http://localhost:3000/ebay/callback
EBAY_RU_NAME=your_runame

# eBay Business Policies (optional - can be created via UI)
EBAY_DEFAULT_SHIPPING_POLICY_ID=
EBAY_DEFAULT_RETURN_POLICY_ID=
EBAY_DEFAULT_PAYMENT_POLICY_ID=
```

---

## Dependencies

### Backend (Python)
```bash
pip install ebay-oauth-python-client
pip install requests
pip install pillow  # Already installed for image processing
pip install cryptography  # For token encryption
```

### Frontend (TypeScript)
```bash
npm install @tanstack/react-query  # For API state management
npm install react-dropzone  # For image uploads (if not already)
```

---

## Implementation Timeline

### Week 1: Foundation
- [ ] Database schema and models
- [ ] OAuth service implementation
- [ ] Basic API endpoints
- [ ] Frontend auth component

### Week 2: Core Listing
- [ ] Inventory service
- [ ] Image upload service
- [ ] Listing orchestrator
- [ ] Frontend listing preview

### Week 3: Failure Handling
- [ ] Failure tracking system
- [ ] Retry mechanism
- [ ] Error UI components
- [ ] Testing failure scenarios

### Week 4: Polish & Testing
- [ ] End-to-end testing
- [ ] Sandbox testing
- [ ] Documentation
- [ ] Production deployment

---

## Success Metrics

- **Listing Success Rate**: >95% of valid listings published
- **Auth Reliability**: <1% token refresh failures
- **Retry Effectiveness**: >80% of transient failures recovered
- **User Satisfaction**: Clear error messages, easy recovery
- **Performance**: <30s average listing creation time

---

## Security Considerations

1. **Token Storage**: Encrypt OAuth tokens in database
2. **Token Rotation**: Handle refresh token rotation
3. **Rate Limiting**: Respect eBay API rate limits
4. **Input Validation**: Validate all user inputs
5. **Error Messages**: Don't expose sensitive info in errors
6. **Audit Logging**: Log all eBay API calls for debugging

---

## Future Enhancements

- Multi-platform support (Amazon, Walmart)
- Bulk listing creation
- Scheduled listings
- Inventory sync
- Sales analytics
- Automatic repricing
- Cross-posting to multiple platforms
