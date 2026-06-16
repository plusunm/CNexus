#!/usr/bin/env sh
# CNexus Product — UI only (Demo mode, no backend required)
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then npm install; fi
echo "CNexus Product → http://localhost:3000 (Demo mode works without API)"
npm run dev
