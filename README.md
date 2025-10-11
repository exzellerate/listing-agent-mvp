# Listing Agent MVP

An AI-powered marketplace listing generator that uses Claude Vision API to analyze product images and automatically generate optimized listings for eBay, Amazon, and Walmart.

## Features

- **AI Image Analysis**: Upload product images and get instant AI-powered analysis
- **Multi-Platform Support**: Generate optimized listings for eBay, Amazon, and Walmart
- **Smart Content Generation**:
  - Platform-specific title optimization (respects character limits)
  - Professional product descriptions
  - Automatic feature extraction
  - Condition assessment
- **Interactive Editing**: Edit and customize all generated content
- **Copy to Clipboard**: Quick copy buttons for all fields
- **Modern UI**: Clean, responsive design with Tailwind CSS

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Anthropic Claude API** - Claude 3.5 Sonnet with vision capabilities
- **Python 3.8+** - With type hints and async support
- **Pydantic** - Data validation and settings management

### Frontend
- **React 18** - UI library
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework

## Project Structure

```
listing-agent-mvp/
├── README.md
├── backend/
│   ├── main.py                      # FastAPI application
│   ├── models.py                    # Pydantic models
│   ├── requirements.txt             # Python dependencies
│   ├── .env.example                 # Environment variables template
│   └── services/
│       └── claude_analyzer.py       # Claude API integration
└── frontend/
    ├── src/
    │   ├── App.tsx                  # Main application component
    │   ├── main.tsx                 # React entry point
    │   ├── index.css                # Global styles with Tailwind
    │   ├── components/
    │   │   ├── ImageUpload.tsx      # Drag-and-drop image upload
    │   │   ├── PlatformSelector.tsx # Platform selection buttons
    │   │   ├── LoadingState.tsx     # Loading spinner
    │   │   ├── ResultsForm.tsx      # Editable results form
    │   │   └── CopyButton.tsx       # Copy to clipboard button
    │   ├── services/
    │   │   └── api.ts               # Backend API calls
    │   └── types/
    │       └── index.ts             # TypeScript interfaces
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    ├── tailwind.config.js
    └── postcss.config.js
```

## Setup Instructions

### Prerequisites

- **Python 3.8+** installed
- **Node.js 18+** and npm installed
- **Anthropic API Key** (get one at https://console.anthropic.com/)

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd listing-agent-mvp/backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv

   # On macOS/Linux:
   source venv/bin/activate

   # On Windows:
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

5. Edit `.env` and add your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_actual_api_key_here
   ```

6. Run the backend server:
   ```bash
   python main.py
   ```

   The backend will start on `http://localhost:8000`

### Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd listing-agent-mvp/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

   The frontend will start on `http://localhost:5173`

4. Open your browser and visit `http://localhost:5173`

## Usage Guide

1. **Select a Platform**: Choose between eBay, Amazon, or Walmart
2. **Upload an Image**:
   - Click the upload area or drag and drop a product image
   - Supported formats: JPG, PNG, GIF, WebP (max 10MB)
3. **Analyze**: Click the "Analyze Image" button
4. **Review Results**: The AI will generate:
   - Product name, brand, category, and condition
   - Platform-optimized title
   - Professional product description
   - Key features list
5. **Edit & Copy**:
   - Edit any field as needed
   - Use the "Copy" buttons to copy content to clipboard
   - Add or remove features from the list

## API Endpoints

### `POST /api/analyze`

Analyzes a product image and generates listing content.

**Request:**
- Method: `POST`
- Content-Type: `multipart/form-data`
- Body:
  - `file`: Image file (required)
  - `platform`: Target platform - "ebay", "amazon", or "walmart" (optional, default: "ebay")

**Response:**
```json
{
  "product_name": "string",
  "brand": "string | null",
  "category": "string | null",
  "condition": "string",
  "color": "string | null",
  "material": "string | null",
  "model_number": "string | null",
  "key_features": ["string"],
  "suggested_title": "string",
  "suggested_description": "string"
}
```

### `GET /health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "api_key_configured": true
}
```

## Platform-Specific Guidelines

### eBay
- **Title Length**: 80 characters max
- **Focus**: Keyword-rich, include brand, model, features, and condition
- **Style**: Concise, searchable

### Amazon
- **Title Length**: 200 characters max
- **Focus**: Brand + Model + Key Features + Size/Color
- **Style**: Proper capitalization, detailed

### Walmart
- **Title Length**: 75 characters max
- **Focus**: Brand, product type, 1-2 key features
- **Style**: Simple and direct

## Development

### Backend Development

Run with auto-reload:
```bash
cd backend
python main.py
```

The server will automatically reload when you make changes to the code.

### Frontend Development

Run dev server:
```bash
cd frontend
npm run dev
```

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## Troubleshooting

### Backend Issues

**Problem**: `ANTHROPIC_API_KEY not set` error
- **Solution**: Make sure you created a `.env` file in the `backend/` directory with your API key

**Problem**: Module import errors
- **Solution**: Make sure you activated the virtual environment and installed all requirements

**Problem**: Port 8000 already in use
- **Solution**: Kill the process using port 8000 or change the port in `main.py`

### Frontend Issues

**Problem**: Cannot connect to backend
- **Solution**: Make sure the backend is running on `http://localhost:8000`

**Problem**: `npm install` fails
- **Solution**: Try deleting `node_modules/` and `package-lock.json`, then run `npm install` again

**Problem**: Port 5173 already in use
- **Solution**: The Vite dev server will automatically try the next available port

## Environment Variables

### Backend (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `ANTHROPIC_API_KEY` | Your Anthropic API key from console.anthropic.com | Yes |

## License

MIT License - feel free to use this project for your own purposes.

## Future Enhancements

- [ ] Support for bulk image processing
- [ ] Integration with marketplace APIs for direct listing
- [ ] Save and manage listing drafts
- [ ] Export listings in various formats (CSV, JSON)
- [ ] Multi-language support
- [ ] Price suggestion based on market analysis
- [ ] Image enhancement and background removal
- [ ] Competitor analysis

## Contributing

This is an MVP project. Feel free to fork and customize for your needs!

## Support

For issues with:
- **Claude API**: Visit https://docs.anthropic.com/
- **This project**: Check the troubleshooting section above

---

Built with Claude AI Vision
