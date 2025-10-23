#!/bin/bash

# Start DeepSeek OCR Server

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}DeepSeek OCR Server${NC}"
echo -e "${BLUE}======================================${NC}"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo -e "${YELLOW}Please run setup.sh first or copy .env.example to .env${NC}"
    exit 1
fi

# Check if modules are copied
if [ ! -f "deepseek_ocr.py" ]; then
    echo -e "${RED}Error: deepseek_ocr.py not found${NC}"
    echo -e "${YELLOW}Please run setup.sh first to copy required modules${NC}"
    exit 1
fi

# Load environment variables
source .env

echo -e "${GREEN}Configuration:${NC}"
echo -e "  Model Path: ${MODEL_PATH}"
echo -e "  CUDA Device: ${CUDA_VISIBLE_DEVICES}"
echo -e "  Server Port: ${SERVER_PORT}"
echo -e "  Max Concurrency: ${MAX_CONCURRENCY}"
echo ""

# Check if port is already in use
if lsof -Pi :${SERVER_PORT} -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo -e "${YELLOW}Warning: Port ${SERVER_PORT} is already in use${NC}"
    echo -e "Please stop the existing service or change SERVER_PORT in .env"
    exit 1
fi

# Start server
echo -e "${GREEN}Starting DeepSeek OCR Server...${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
echo ""

# Run the server
python3 app.py
