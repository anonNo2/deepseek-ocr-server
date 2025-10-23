#!bin/bash

# DeepSeek OCR Server Setup Script

set -e

echo "=========================================="
echo "DeepSeek OCR Server Setup"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running in the correct directory
if [ ! -f "app.py" ]; then
    echo -e "${RED}Error: Please run this script from the deepsee-ocr-server directory${NC}"
    exit 1
fi

echo -e "${GREEN}Step 1: Copying DeepSeek OCR modules...${NC}"

# Source directory
SOURCE_DIR="../DeepSeek-OCR/DeepSeek-OCR-master/DeepSeek-OCR-vllm"

if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source directory not found: $SOURCE_DIR${NC}"
    exit 1
fi

# Copy required modules
echo "Copying deepseek_ocr.py..."
cp "$SOURCE_DIR/deepseek_ocr.py" .

echo "Copying deepencoder directory..."
cp -r "$SOURCE_DIR/deepencoder" .

echo "Copying process directory..."
cp -r "$SOURCE_DIR/process" .

echo -e "${GREEN}✓ Modules copied successfully${NC}"

echo -e "${GREEN}Step 2: Setting up environment...${NC}"

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo -e "${YELLOW}⚠ Please edit .env file to configure your settings${NC}"
else
    echo ".env file already exists"
fi

# Create temp directory
echo "Creating temp directory..."
mkdir -p temp

echo -e "${GREEN}✓ Environment setup complete${NC}"

echo -e "${GREEN}Step 3: Installing Python dependencies...${NC}"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}Error: pip3 is not installed${NC}"
    exit 1
fi

# Install dependencies
pip3 install -r requirements.txt

echo -e "${GREEN}✓ Dependencies installed successfully${NC}"

echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file to configure your settings"
echo "2. Make sure MODEL_PATH points to your DeepSeek OCR model"
echo "3. Run the server:"
echo "   python3 app.py"
echo ""
echo "Or use Docker:"
echo "   docker-compose up -d"
echo ""
echo "For VSCode debugging, press F5 in VSCode"
echo ""
