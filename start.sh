#!/bin/bash
# RichMan - 中国股市量化分析平台 启动脚本

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  ____  _          __  __   _    _   _ _   _ __  __ "
echo " |  _ \(_)_ __ ___|  \/  | / \  | \ | | \ | |  \/  |"
echo " | |_) | | '__/ _ \ |\/| |/ _ \ |  \| |  \| | |\/| |"
echo " |  _ <| | | |  __/ |  | / ___ \| |\  | |\  | |  | |"
echo " |_| \_\_|_|  \___|_|  |_/_/   \_\_| \_|_| \_|_|  |_|"
echo -e "${NC}"
echo "  中国股市量化分析平台（前端已重构为 TypeScript）"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python3 not found. Please install Python 3.9+${NC}"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi

# Prefer pnpm for frontend
if command -v pnpm &> /dev/null; then
    FE_PM="pnpm"
else
    FE_PM="npm"
fi

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Setup Python virtual environment
VENV_DIR="$PROJECT_DIR/backend/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${BLUE}[1/4] Creating Python virtual environment...${NC}"
    # Ensure python3-venv is installed (required on Debian/Ubuntu)
    if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
        echo -e "${YELLOW}[INFO] Installing python3-venv...${NC}"
        sudo apt-get update -qq && sudo apt-get install -y -qq python3-venv 2>/dev/null || \
        sudo apt install -y -qq python3.12-venv 2>/dev/null || true
        python3 -m venv "$VENV_DIR"
    fi
fi
source "$VENV_DIR/bin/activate"

# Install backend dependencies
echo -e "${BLUE}[2/4] Installing backend dependencies...${NC}"
cd "$PROJECT_DIR/backend"
pip install -r requirements.txt -q

# Install frontend dependencies (pnpm preferred)
echo -e "${BLUE}[3/4] Installing frontend dependencies...${NC}"
cd "$PROJECT_DIR/frontend"
if [ "$FE_PM" = "pnpm" ]; then
    pnpm install
else
    npm install --legacy-peer-deps
fi

# Start backend
echo -e "${BLUE}[4/4] Starting backend server (port 5000)...${NC}"
cd "$PROJECT_DIR/backend"
python app.py &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3

# Start frontend
echo -e "${BLUE}[4/4] Starting frontend dev server (port 3000)...${NC}"
cd "$PROJECT_DIR/frontend"
npx vite --port 3000 --host &
FRONTEND_PID=$!

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  RichMan is running!${NC}"
echo -e "${GREEN}  Frontend: http://localhost:3000${NC}"
echo -e "${GREEN}  Backend:  http://localhost:5000${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Press Ctrl+C to stop all services"

# Trap Ctrl+C
trap "echo -e '\n${RED}Stopping services...${NC}'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" INT TERM

wait
