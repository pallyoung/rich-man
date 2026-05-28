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

# ─── Environment preflight checks ───────────────────────────────────
echo -e "${BLUE}[0/5] Checking environment prerequisites...${NC}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[ERROR] Python3 not found. Please install Python 3.9+${NC}"
    exit 1
fi
PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}  ✓ Python $PY_VER${NC}"

# Check Node
if ! command -v node &> /dev/null; then
    echo -e "${RED}[ERROR] Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi
NODE_VER=$(node -v)
echo -e "${GREEN}  ✓ Node.js $NODE_VER${NC}"

# Prefer pnpm for frontend
if command -v pnpm &> /dev/null; then
    FE_PM="pnpm"
    echo -e "${GREEN}  ✓ pnpm $(pnpm -v)${NC}"
else
    FE_PM="npm"
    echo -e "${GREEN}  ✓ npm $(npm -v)${NC}"
fi

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo -e "${GREEN}  ✓ PROJECT_DIR=$PROJECT_DIR${NC}"
echo ""

# ─── Setup Python virtual environment ───────────────────────────────
VENV_DIR="$PROJECT_DIR/backend/venv"
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo -e "${BLUE}[1/5] Creating Python virtual environment...${NC}"
    [ -d "$VENV_DIR" ] && rm -rf "$VENV_DIR"

    # Try creating venv; if ensurepip is missing, install python3-venv and retry
    if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
        echo -e "${YELLOW}  ensurepip not available, installing python3-venv...${NC}"
        # Detect the correct package name (e.g. python3.12-venv)
        VENV_PKG="python3${PY_VER:+${PY_VER}}-venv"
        sudo apt-get update -qq
        sudo apt-get install -y -qq "$VENV_PKG" || sudo apt-get install -y -qq python3-venv
        # Retry
        [ -d "$VENV_DIR" ] && rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
    fi

    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        echo -e "${RED}[ERROR] Failed to create venv. Run manually:${NC}"
        echo -e "${RED}  sudo apt install python3-venv && python3 -m venv $VENV_DIR${NC}"
        exit 1
    fi
    echo -e "${GREEN}  ✓ venv created${NC}"
else
    echo -e "${GREEN}[1/5] Virtual environment already exists.${NC}"
fi
source "$VENV_DIR/bin/activate"

# ─── Install backend dependencies ──────────────────────────────────
echo -e "${BLUE}[2/5] Installing backend dependencies...${NC}"
cd "$PROJECT_DIR/backend"
pip install -r requirements.txt -q

# ─── Install frontend dependencies ─────────────────────────────────
echo -e "${BLUE}[3/5] Installing frontend dependencies...${NC}"
cd "$PROJECT_DIR/frontend"
if [ "$FE_PM" = "pnpm" ]; then
    pnpm install --ignore-workspace
else
    npm install --legacy-peer-deps
fi

# ─── Start backend ─────────────────────────────────────────────────
echo -e "${BLUE}[4/5] Starting backend server (port 5000)...${NC}"
cd "$PROJECT_DIR/backend"
python app.py &
BACKEND_PID=$!

# Wait for backend to be ready
sleep 3

# ─── Start frontend ────────────────────────────────────────────────
echo -e "${BLUE}[5/5] Starting frontend dev server (port 3000)...${NC}"
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
