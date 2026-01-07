# eBay Integration Setup Guide

This guide will help you set up the eBay integration for the Listing Agent MVP to post listings directly to eBay.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [eBay Developer Account Setup](#ebay-developer-account-setup)
3. [Creating an eBay Application](#creating-an-ebay-application)
4. [Setting Up Business Policies](#setting-up-business-policies)
5. [Configuring the Application](#configuring-the-application)
6. [Database Migration](#database-migration)
7. [Testing with Sandbox](#testing-with-sandbox)
8. [Going Live](#going-live)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Active eBay seller account
- Python 3.9+ installed
- Backend server running locally
- Basic understanding of OAuth 2.0

---

## eBay Developer Account Setup

### Step 1: Create Developer Account

1. Go to [eBay Developers Program](https://developer.ebay.com/)
2. Click "Register" and sign in with your eBay account
3. Accept the eBay Developers Program License Agreement
4. Complete your developer profile

### Step 2: Get Your Keys

1. Navigate to "Hi [YourName]" → "Application Keys"
2. You'll see two environments:
   - **Sandbox** (for testing)
   - **Production** (for live listings)

---

## Creating an eBay Application

### Step 1: Create Application Keyset

1. In the Developer Portal, click "Create a keyset"
2. Choose "Sell" API as your primary API
3. Note down:
   - **App ID (Client ID)**
   - **Cert ID (Client Secret)**

### Step 2: Configure OAuth Redirect URI

1. Go to "User Tokens" section
2. Click "Get OAuth Redirect URI"
3. Create an RuName (Redirect URL Name):
   - **Your redirect URL**: `http://localhost:3000/ebay/callback`
   - **Your privacy policy URL**: (your privacy policy URL)
4. Note down the **RuName** - you'll need this

### Step 3: Grant Application Access

1. Navigate to "User Tokens"
2. Click "Get a User Token Here"
3. Sign in and authorize the application
4. This grants your app access to your eBay account

---

## Setting Up Business Policies

eBay requires business policies for listings. You need to create:
- **Shipping Policy**
- **Return Policy**
- **Payment Policy**

### Option 1: Create in eBay Seller Hub (Recommended)

1. Go to [eBay Seller Hub](https://www.ebay.com/sh/ovw)
2. Navigate to "Account" → "Site Preferences" → "Business Policies"
3. Create policies for:
   - Shipping (domestic/international rates, handling time)
   - Returns (return period, who pays return shipping)
   - Payment (payment methods accepted)
4. Note down the **Policy IDs** for each

### Option 2: Create via API

You can also create policies programmatically using the eBay Account API:
- [Account API Documentation](https://developer.ebay.com/api-docs/sell/account/overview.html)

---

## Configuring the Application

### Step 1: Update Environment Variables

Copy the example configuration:

```bash
cd backend
cp .env.example .env
```

### Step 2: Add eBay Credentials

Edit `.env` and add your eBay credentials:

```bash
# eBay API Configuration
EBAY_ENV=SANDBOX  # Start with SANDBOX for testing
EBAY_CLIENT_ID=YourAppID_Here
EBAY_CLIENT_SECRET=YourCertID_Here
EBAY_REDIRECT_URI=http://localhost:3000/ebay/callback
EBAY_RU_NAME=YourRuName_Here

# eBay Business Policies
EBAY_DEFAULT_SHIPPING_POLICY_ID=your_shipping_policy_id
EBAY_DEFAULT_RETURN_POLICY_ID=your_return_policy_id
EBAY_DEFAULT_PAYMENT_POLICY_ID=your_payment_policy_id
```

### Step 3: Install Dependencies

```bash
pip install ebay-oauth-python-client
```

---

## Database Migration

The eBay integration adds new database tables. Migrate your database:

```bash
cd backend
source venv/bin/activate
python -c "from database import init_db; init_db()"
```

This creates:
- `ebay_credentials` - Stores OAuth tokens
- `ebay_listings` - Tracks listing status
- `ebay_listing_failures` - Detailed failure tracking

---

## Testing with Sandbox

### Step 1: Use Sandbox Environment

Ensure your `.env` has:

```bash
EBAY_ENV=SANDBOX
```

### Step 2: Get Sandbox User Token

1. Go to [eBay Sandbox](https://sandbox.ebay.com/)
2. Create a test buyer and seller account
3. In Developer Portal, get a **Sandbox User Token**
4. Test the OAuth flow with your sandbox account

### Step 3: Create Test Listing

```bash
# Start the backend
python main.py
```

Use the frontend or API to:
1. Authenticate with eBay Sandbox
2. Create a test listing
3. Verify it appears in [Sandbox Seller Hub](https://sell.sandbox.ebay.com/)

### Sandbox Limitations

- Sandbox has limited functionality
- Some categories may not work
- Payments are simulated
- Listings don't appear on public eBay

---

## Going Live

### Step 1: Switch to Production Keys

1. In eBay Developer Portal, get **Production** keys
2. Create production RuName with same redirect URI
3. Update `.env`:

```bash
EBAY_ENV=PRODUCTION
EBAY_CLIENT_ID=ProductionAppID
EBAY_CLIENT_SECRET=ProductionCertID
EBAY_RU_NAME=ProductionRuName
```

### Step 2: Production OAuth Flow

1. User must re-authenticate with production credentials
2. Grant permissions via OAuth flow
3. Tokens are stored in database

### Step 3: Create Real Listing

Test with a real product:
1. Analyze product images
2. Review generated listing
3. Post to eBay
4. Verify listing appears on eBay.com

### Step 4: Monitor for Errors

Check logs for:
- Authentication failures
- Rate limiting issues
- Policy violations
- Category errors

---

## Troubleshooting

### Authentication Errors

**Error**: `INVALID_TOKEN` or `INVALID_CREDENTIALS`

**Solutions**:
- Verify Client ID and Secret are correct
- Check if token is expired (tokens expire ~2 hours)
- Ensure RuName matches configured redirect URI
- Re-run OAuth flow to get fresh tokens

### Rate Limiting

**Error**: `RATE_LIMIT_EXCEEDED`

**Solutions**:
- eBay has API call limits per day
- Sandbox: 5,000 calls/day
- Production: Higher limits based on account
- Implement exponential backoff (already built-in)
- Wait and retry automatically

### Category Errors

**Error**: `INVALID_CATEGORY`

**Solutions**:
- Use eBay's Category API to find valid categories
- Some categories require item specifics
- Check [eBay Category Changes](https://developer.ebay.com/support/kb-article?KBid=4877)

### Image Upload Failures

**Error**: `IMAGE_TOO_LARGE` or `INVALID_IMAGE_FORMAT`

**Solutions**:
- Max image size: 12MB
- Supported formats: JPEG, PNG, GIF, BMP, TIFF
- Minimum dimensions: 500x500 pixels
- Maximum 12 images per listing

### Business Policy Errors

**Error**: `MISSING_POLICY`

**Solutions**:
- Verify policy IDs are correct
- Policies must be created for your marketplace (EBAY_US)
- Check policies are active in Seller Hub

### Duplicate SKU

**Error**: `DUPLICATE_SKU`

**Solutions**:
- Each listing needs unique SKU
- System auto-generates SKUs: `LA-TIMESTAMP-RANDOM`
- If collision occurs, retry automatically generates new SKU

---

## API Call Limits

### Sandbox Environment

- **Per Day**: 5,000 calls
- **Per Second**: No limit
- **Burst**: Unlimited

### Production Environment

Limits vary by seller level:

| Seller Level | Calls/Day | Calls/Second |
|--------------|-----------|--------------|
| New Seller   | 5,000     | 1            |
| Above Standard | 25,000  | 5            |
| Top Rated    | 100,000   | 10           |

Monitor your usage in the eBay Developer Portal.

---

## Security Best Practices

### 1. Protect Credentials

- **Never** commit `.env` file to git
- Use environment variables in production
- Rotate keys periodically

### 2. Token Management

- Tokens are stored encrypted in database
- Auto-refresh before expiry
- Revoke tokens when not needed

### 3. Input Validation

- All listing data is validated before API calls
- Prevents injection attacks
- Sanitizes user input

### 4. HTTPS in Production

- Use HTTPS for OAuth redirect URI
- Secure token transmission
- Update redirect URI in eBay Developer Portal

---

## Support Resources

- **eBay Developer Forums**: https://community.ebay.com/t5/Developer-Forums/ct-p/ebay-developer
- **eBay API Documentation**: https://developer.ebay.com/docs
- **OAuth Guide**: https://developer.ebay.com/api-docs/static/oauth-tokens.html
- **Inventory API**: https://developer.ebay.com/api-docs/sell/inventory/overview.html
- **Support Tickets**: https://developer.ebay.com/support

---

## Next Steps

After successful setup:

1. ✅ Complete OAuth flow in frontend
2. ✅ Test listing creation end-to-end
3. ✅ Monitor failure rates and errors
4. ✅ Implement retry logic for transient errors
5. ✅ Set up monitoring/alerting for production
6. ✅ Create analytics dashboard for listing performance

---

## Quick Reference

### Environment Variables

```bash
# Required
EBAY_ENV=SANDBOX|PRODUCTION
EBAY_CLIENT_ID=your_app_id
EBAY_CLIENT_SECRET=your_cert_id
EBAY_REDIRECT_URI=http://localhost:3000/ebay/callback
EBAY_RU_NAME=your_runame

# Optional
EBAY_DEFAULT_SHIPPING_POLICY_ID=policy_id
EBAY_DEFAULT_RETURN_POLICY_ID=policy_id
EBAY_DEFAULT_PAYMENT_POLICY_ID=policy_id
```

### API Endpoints

```
GET  /api/ebay/auth/url          - Get OAuth authorization URL
POST /api/ebay/auth/callback     - Handle OAuth callback
GET  /api/ebay/auth/status       - Check authentication status
DELETE /api/ebay/auth/revoke     - Revoke credentials

POST /api/ebay/listings/create   - Create new listing
GET  /api/ebay/listings/:id      - Get listing status
POST /api/ebay/listings/:id/retry - Retry failed listing
DELETE /api/ebay/listings/:id    - Cancel listing
GET  /api/ebay/listings          - List all listings
```

### Common eBay Item Conditions

- `NEW` - Brand new item
- `NEW_WITH_DEFECTS` - New with defects
- `MANUFACTURER_REFURBISHED` - Manufacturer refurbished
- `SELLER_REFURBISHED` - Seller refurbished
- `USED_EXCELLENT` - Used, excellent condition
- `USED_VERY_GOOD` - Used, very good condition
- `USED_GOOD` - Used, good condition
- `USED_ACCEPTABLE` - Used, acceptable condition
- `FOR_PARTS_OR_NOT_WORKING` - For parts or not working

---

## Checklist

Before going live, ensure:

- [ ] eBay Developer account created
- [ ] Production application keys obtained
- [ ] RuName configured with correct redirect URI
- [ ] Business policies created (shipping, return, payment)
- [ ] Environment variables configured
- [ ] Database migrated with eBay tables
- [ ] Tested full flow in Sandbox
- [ ] OAuth flow working correctly
- [ ] Listing creation successful
- [ ] Error handling tested
- [ ] Failure retry mechanism working
- [ ] Monitoring and logging in place

---

**Ready to start selling!** 🚀
