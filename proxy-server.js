/**
 * Simple reverse proxy server for Cloudflare Tunnel
 * Routes /api/* and /uploads/* to backend (8000)
 * Routes everything else to frontend (5173)
 */

const http = require('http');
const httpProxy = require('http-proxy');

const proxy = httpProxy.createProxyServer({
  proxyTimeout: 600000, // 10 minutes (600 seconds) for long-running image analysis
  timeout: 600000, // 10 minutes socket timeout
});
const PORT = 3001;

// Handle proxy errors
proxy.on('error', (err, req, res) => {
  console.error('Proxy error:', err);
  res.writeHead(500, { 'Content-Type': 'text/plain' });
  res.end('Proxy error');
});

const server = http.createServer((req, res) => {
  console.log(`${req.method} ${req.url}`);

  // Route API requests to backend (keep /api prefix)
  if (req.url.startsWith('/api/')) {
    console.log('  -> Backend (8000)');
    proxy.web(req, res, { target: 'http://localhost:8000' });
  }
  // Route uploads to backend (keep path as-is)
  else if (req.url.startsWith('/uploads/')) {
    console.log('  -> Backend (8000)');
    proxy.web(req, res, { target: 'http://localhost:8000' });
  }
  // Route everything else to frontend
  else {
    console.log('  -> Frontend (5173)');
    proxy.web(req, res, { target: 'http://localhost:5173' });
  }
});

// Set server timeout to 10 minutes (600 seconds)
server.setTimeout(600000);
server.keepAliveTimeout = 605000; // Slightly longer than setTimeout
server.headersTimeout = 610000; // Slightly longer than keepAliveTimeout

server.listen(PORT, () => {
  console.log(`Proxy server running on port ${PORT}`);
  console.log('Timeouts configured: 600s (10 minutes)');
  console.log('Routes:');
  console.log('  /api/*     -> http://localhost:8000');
  console.log('  /uploads/* -> http://localhost:8000');
  console.log('  /*         -> http://localhost:5173');
});
