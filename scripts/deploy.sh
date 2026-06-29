#!/bin/bash
# ==========================================
#  KwachaCast - Deployment Script
#  Usage: bash scripts/deploy.sh
# ==========================================

echo "=========================================="
echo "  KwachaCast - Deployment"
echo "=========================================="
echo ""

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo "⚠️  Uncommitted changes found:"
    git status -s
    echo ""
    read -p "Commit and push anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "📦 Step 1: Building frontend..."
cd frontend
npm run build
cd ..
echo "   Build complete"

echo ""
echo "📤 Step 2: Committing and pushing to GitHub..."
git add .
git commit -m "Deploy: $(date +'%Y-%m-%d %H:%M')" 2>/dev/null || echo "   No new changes to commit"
git push origin main
echo "   Code pushed to GitHub"

echo ""
echo "📡 Step 3: Deployment triggered!"
echo "   GitHub Actions will automatically deploy:"
echo "   • Backend → Render"
echo "   • Frontend → Vercel"
echo ""
echo "🔗 Check deployment status:"
echo "   https://github.com/Kennywryght/kwacha-forecasting/actions"
echo ""
echo "✅ Done!"