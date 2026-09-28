# Kill whatever's on the Vite port, if anything
lsof -ti:5173 | xargs kill 2>/dev/null

# Start the frontend dev server (now serves https://localhost:5173)
cd /Users/tuhin/listing-agent-mvp/frontend && npm run dev

# Backend, in a separate terminal (only needed if it's not already running)
cd /Users/tuhin/listing-agent-mvp/backend && source venv/bin/activate && uvicorn main:app --reload --port 8000
