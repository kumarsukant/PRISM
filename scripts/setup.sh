#!/bin/bash

# Prism Project Setup Script
# This script initializes the Prism development environment
# Run: bash scripts/setup.sh

set -e  # Exit on error

echo "🎨 Prism — Setting up project environment..."
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"

command -v python3 >/dev/null 2>&1 || { echo "❌ Python 3.12+ required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js 20+ required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker required"; exit 1; }

echo -e "${GREEN}✅ Prerequisites met${NC}"
echo ""

# Set up backend
echo -e "${BLUE}Step 2: Setting up backend...${NC}"
cd backend
python3 -m venv venv

# Activate venv
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo -e "${GREEN}✅ Backend setup complete${NC}"
echo ""

# Set up frontend
echo -e "${BLUE}Step 3: Setting up frontend...${NC}"
cd ../frontend
npm install

echo -e "${GREEN}✅ Frontend setup complete${NC}"
echo ""

# Create .env files
echo -e "${BLUE}Step 4: Creating .env files...${NC}"

# Backend .env
if [ ! -f "backend/.env" ]; then
    cat > backend/.env << 'EOF'
# Backend Environment Variables
DATABASE_URL=postgresql://prism:prism@localhost:5432/prism_db
REDIS_URL=redis://localhost:6379
OLLAMA_URL=http://localhost:11434
JWT_SECRET=dev-secret-key-change-in-production
STRIPE_SECRET_KEY=sk_test_xxx
ENVIRONMENT=development
DEBUG=True
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✅ Created backend/.env${NC}"
fi

# Frontend .env.local
if [ ! -f "frontend/.env.local" ]; then
    cat > frontend/.env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STRIPE_PUBLIC_KEY=pk_test_xxx
NEXT_PUBLIC_ENVIRONMENT=development
EOF
    echo -e "${GREEN}✅ Created frontend/.env.local${NC}"
fi

echo ""

# Initialize git (if not already)
if [ ! -d ".git" ]; then
    echo -e "${BLUE}Step 5: Initializing Git repository...${NC}"
    git init
    git add .
    git commit -m "Initial commit: Prism project structure"
    echo -e "${GREEN}✅ Git repository initialized${NC}"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✨ Prism setup complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📖 Next steps:"
echo ""
echo "1. Start Ollama (Terminal 1):"
echo "   ollama serve"
echo ""
echo "2. Start backend (Terminal 2):"
echo "   cd backend"
echo "   source venv/bin/activate  # or venv\\Scripts\\activate on Windows"
echo "   uvicorn app.main:app --reload --port 8000"
echo ""
echo "3. Start frontend (Terminal 3):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "4. Open browser:"
echo "   http://localhost:3000"
echo ""
echo "📚 Documentation:"
echo "   - Brand guidelines: brand/BRAND_GUIDELINES.md"
echo "   - Architecture: docs/ARCHITECTURE.md"
echo "   - API docs: docs/API.md"
echo ""
echo "Happy coding! 🚀"
