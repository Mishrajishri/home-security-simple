#!/usr/bin/env bash
cd "$(dirname "$0")"
export PATH="$HOME/.local/node/bin:$PATH"
echo "🚀 Starting Home Automation Dashboard Server..."
node server/server.js
