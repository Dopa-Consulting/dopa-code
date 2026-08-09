#!/usr/bin/env bash
# Loop Doctor — Top-3 diagnostic actions for Inti
set -e

echo "=== Loop Doctor — Diagnosing Dopa Code Inti ==="
echo ""

# 1. Check Python models
echo "[1/3] Python database models..."
cd backend-inti
MODELS=$(python -c "from inti.database import Base; print(len(Base.metadata.tables))" 2>/dev/null || echo "0")
echo "   Models registered: $MODELS (expected: 16+)"

# 2. Check frontend build
echo "[2/3] Frontend TypeScript check..."
cd ../frontend-pwa
npx tsc --noEmit 2>/dev/null && echo "   TypeScript: 0 errors" || echo "   TypeScript: errors found"

# 3. Check plugins
echo "[3/3] Plugins discovery..."
cd ..
PLUGINS=$(find plugins -name "plugin.json" 2>/dev/null | wc -l)
echo "   Plugins found: $PLUGINS (expected: 2+)"

echo ""
echo "=== Top-3 Recommended Actions ==="
echo "1. Review TypeScript errors before deploying to production"
echo "2. Verify all 16+ database models are registered in main.py"
echo "3. Run 'uvicorn main:app --reload' to test locally before push"
echo ""
echo "Loop Ready Score: $([ $PLUGINS -ge 2 ] && echo '9/10' || echo '6/10')"
