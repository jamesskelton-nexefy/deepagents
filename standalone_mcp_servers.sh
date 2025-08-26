#!/usr/bin/env bash

# === CONFIGURATION ===
# -- Edit these with your REAL keys/port if needed
FIRECRAWL_API_KEY="your_firecrawl_api_key_here"
REPLICATE_API_TOKEN="your_replicate_api_token_here"
FIRECRAWL_PORT=3001
REPLICATE_PORT=3002

echo "🚀 Starting Standalone MCP Servers"
echo "=================================="

# === FIRECRAWL MCP SERVER ===
echo "Starting Firecrawl MCP server on port $FIRECRAWL_PORT..."
env SSE_LOCAL=true FIRECRAWL_API_KEY="$FIRECRAWL_API_KEY" npx -y firecrawl-mcp --port "$FIRECRAWL_PORT" > firecrawl_mcp.log 2>&1 &
FC_PID=$!
echo "✅ Firecrawl MCP PID: $FC_PID (logs: firecrawl_mcp.log)"
echo "   SSE Endpoint: http://localhost:$FIRECRAWL_PORT/sse"

# === REPLICATE MCP SERVER ===
echo "Starting Replicate MCP server on port $REPLICATE_PORT..."
env REPLICATE_API_TOKEN="$REPLICATE_API_TOKEN" npx -y replicate-mcp --port "$REPLICATE_PORT" > replicate_mcp.log 2>&1 &
REP_PID=$!
echo "✅ Replicate MCP PID: $REP_PID (logs: replicate_mcp.log)"
echo "   SSE Endpoint: http://localhost:$REPLICATE_PORT/sse"

# Wait a moment for servers to start
echo ""
echo "⏳ Waiting for servers to initialize..."
sleep 3

# Test connectivity
echo ""
echo "🔍 Testing server connectivity..."
if curl -s "http://localhost:$FIRECRAWL_PORT/sse" > /dev/null 2>&1; then
    echo "✅ Firecrawl server is responding"
else
    echo "❌ Firecrawl server not responding (check firecrawl_mcp.log)"
fi

if curl -s "http://localhost:$REPLICATE_PORT/sse" > /dev/null 2>&1; then
    echo "✅ Replicate server is responding"
else
    echo "❌ Replicate server not responding (check replicate_mcp.log)"
fi

echo ""
echo "🎯 Server Information:"
echo "======================================"
echo "Firecrawl SSE: http://localhost:$FIRECRAWL_PORT/sse"
echo "Replicate SSE: http://localhost:$REPLICATE_PORT/sse"
echo ""
echo "📋 Process Management:"
echo "To stop both servers: kill $FC_PID $REP_PID"
echo "To view logs: tail -f firecrawl_mcp.log replicate_mcp.log"
echo ""
echo "🔧 Configuration for .env:"
echo "FIRECRAWL_SSE_URL=http://localhost:$FIRECRAWL_PORT/sse"
echo "REPLICATE_SSE_URL=http://localhost:$REPLICATE_PORT/sse"
echo ""
echo "🚀 Ready! You can now start LangGraph with: cd examples/research && langgraph dev"

# Keep script running to show real-time logs
echo ""
echo "📜 Real-time logs (Ctrl+C to stop servers):"
echo "==========================================="
trap "echo ''; echo '🛑 Stopping servers...'; kill $FC_PID $REP_PID 2>/dev/null; exit 0" INT
tail -f firecrawl_mcp.log replicate_mcp.log
