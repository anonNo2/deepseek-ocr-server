# DeepSeek OCR Server

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

A production-ready FastAPI service for converting PDF documents to Markdown using DeepSeek OCR with GPU acceleration.

[English](README.md) | [简体中文](README_CN.md)

## Features

- **PDF to Markdown Conversion** - High-quality document conversion with OCR
- **Asynchronous Processing** - Non-blocking task queue with status tracking
- **RESTful API** - Clean, well-documented API endpoints
- **GPU Acceleration** - CUDA-optimized for high performance
- **Layout Preservation** - Maintains document structure and formatting
- **Bounding Box Visualization** - Visual representation of detected elements
- **Image Extraction** - Extract and save images from documents
- **Docker Support** - Containerized deployment with Docker Compose
- **Production Ready** - Nginx configuration, systemd service, and health checks

## Table of Contents

- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Installation](#installation)
  - [Local Setup](#local-setup)
  - [Docker Setup](#docker-setup)
- [API Usage](#api-usage)
- [Configuration](#configuration)
- [Development](#development)
- [Deployment](#deployment)
- [API Documentation](#api-documentation)
- [Performance Tuning](#performance-tuning)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Requirements

- **Python**: 3.10 or higher
- **GPU**: NVIDIA GPU with CUDA support (recommended)
- **CUDA**: 11.8 or higher
- **Memory**: 16GB+ RAM, 8GB+ GPU VRAM
- **Storage**: 20GB+ for models and temporary files
- **OS**: Linux (Ubuntu 22.04+ recommended)

## Quick Start

### Using Docker (Recommended)

```bash
# 1. Clone and navigate to the project
cd deepseek-ocr-server

# 2. Build and start the service
docker-compose up -d

# 3. Check health
curl http://localhost:8000/health

# 4. Convert a PDF
curl -X POST http://localhost:8000/convert \
  -F "file=@document.pdf" \
  -F "skip_repeat=true" \
  -F "crop_mode=true"
```

### Using Python

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your settings

# 3. Start the server
python app.py
```

## Installation

### Local Setup

#### 1. Prerequisites

Ensure you have CUDA and Python installed:

```bash
# Check CUDA
nvidia-smi

# Check Python
python3 --version
```

#### 2. Clone and Setup

```bash
# Navigate to project directory
cd deepseek-ocr-server

# Run automated setup (copies DeepSeek modules)
bash setup.sh

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit configuration (required)
nano .env
```

Key settings to configure:

```bash
MODEL_PATH=/path/to/DeepSeek-OCR  # Path to DeepSeek OCR model
CUDA_VISIBLE_DEVICES=0             # GPU device ID
SERVER_PORT=8000                   # API server port
```

#### 4. Start the Server

```bash
# Development mode (with auto-reload)
python app.py

# Production mode (with uvicorn)
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

### Docker Setup

#### 1. Build Image

```bash
# Build Docker image
docker build -t deepseek-ocr-server:0.1 .
```

#### 2. Configure Docker Compose

Edit `docker-compose.yml` to set your model path:

```yaml
volumes:
  - /path/to/your/DeepSeek-OCR:/models:ro
```

#### 3. Start Service

```bash
# Start in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop service
docker-compose down
```

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "processor_loaded": true,
  "version": "1.0.0"
}
```

### Convert PDF

```bash
curl -X POST http://localhost:8000/convert \
  -F "file=@document.pdf" \
  -F "prompt=<image>\n<|grounding|>Convert the document to markdown." \
  -F "skip_repeat=true" \
  -F "crop_mode=true"
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "PDF conversion started"
}
```

### Check Task Status

```bash
curl http://localhost:8000/status/{task_id}
```

Response:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "PDF converted successfully",
  "output_file": "/path/to/output.mmd",
  "total_pages": 10,
  "processing_time": 45.2
}
```

### Download Results

```bash
# Download markdown file
curl http://localhost:8000/download/{task_id}/markdown -o output.mmd

# Download markdown with detection info
curl http://localhost:8000/download/{task_id}/markdown_det -o output_det.mmd

# Download PDF with layout annotations
curl http://localhost:8000/download/{task_id}/pdf_layout -o output_layouts.pdf

# Download extracted images as zip
curl http://localhost:8000/download/{task_id}/images_zip -o images.zip
```

### Delete Task

```bash
curl -X DELETE http://localhost:8000/task/{task_id}
```

### Using Python Client

```python
import requests

# Upload PDF
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    data = {'skip_repeat': 'true', 'crop_mode': 'true'}
    response = requests.post('http://localhost:8000/convert', files=files, data=data)
    task_id = response.json()['task_id']

# Check status
status = requests.get(f'http://localhost:8000/status/{task_id}').json()
print(f"Status: {status['status']}")

# Download result
if status['status'] == 'completed':
    result = requests.get(f'http://localhost:8000/download/{task_id}/markdown')
    with open('output.mmd', 'wb') as f:
        f.write(result.content)
```

### Using Provided Client Script

```bash
python api_client.py document.pdf
```

## Configuration

### Environment Variables

The service is configured via the `.env` file:

#### Model Configuration

```bash
MODEL_PATH=/data/models/DeepSeek-OCR  # Path to DeepSeek OCR model weights
CUDA_VISIBLE_DEVICES=0                 # GPU device IDs (comma-separated)
```

#### Performance Settings

```bash
MAX_CONCURRENCY=100                    # Max concurrent OCR operations
NUM_WORKERS=64                         # Image preprocessing workers
GPU_MEMORY_UTILIZATION=0.9             # GPU memory usage (0.0-1.0)
MAX_CONCURRENT_TASKS=8                 # Max parallel PDF processing tasks
```

#### Image Processing

```bash
BASE_SIZE=1024                         # Base image size for processing
IMAGE_SIZE=640                         # Target image size
CROP_MODE=True                         # Enable crop mode for better accuracy
MIN_CROPS=2                            # Minimum crops per image
MAX_CROPS=6                            # Maximum crops per image
SKIP_REPEAT=True                       # Skip pages without EOS token
```

#### Server Settings

```bash
SERVER_HOST=0.0.0.0                    # Server bind address
SERVER_PORT=8000                       # Server port
DEBUG=False                            # Debug mode (True/False)
TEMP_DIR=/tmp/deepseek-ocr-server      # Temporary files directory
MAX_UPLOAD_SIZE=104857600              # Max upload size in bytes (100MB)
```

#### Default Prompt

```bash
DEFAULT_PROMPT="<image>\n<|grounding|>Convert the document to markdown."
```

### Configuration via Docker

Override environment variables in `docker-compose.yml`:

```yaml
environment:
  - MODEL_PATH=/models
  - CUDA_VISIBLE_DEVICES=0
  - MAX_CONCURRENCY=100
  - DEBUG=False
```

## Development

### VSCode Debugging

The project includes VSCode debug configurations. Press `F5` to start debugging.

Available configurations:
- **Python: FastAPI Server** - Development mode with auto-reload
- **Python: FastAPI Server (No Reload)** - Stable debugging without reload
- **Python: Current File** - Debug the currently open file

### Running Tests

```bash
# Run test suite
python test_server.py

# Test async client
python test_async_client.py
```

### Using Makefile

```bash
# Start server
make start

# Run tests
make test

# Clean temporary files
make clean

# Build Docker image
make build

# View all commands
make help
```

### Project Structure

```
deepseek-ocr-server/
├── app.py                    # FastAPI application
├── pdf_processor.py          # PDF processing logic
├── config.py                 # Configuration management
├── deepseek_ocr.py           # DeepSeek OCR model interface
├── deepencoder/              # Model encoder modules
├── process/                  # Image processing utilities
├── api_client.py             # Python API client
├── test_server.py            # Test suite
├── requirements.txt          # Python dependencies
├── .env.example              # Environment template
├── Dockerfile                # Docker image definition
├── docker-compose.yml        # Docker Compose configuration
├── setup.sh                  # Setup script
├── start_server.sh           # Server startup script
├── Makefile                  # Common commands
├── nginx.conf                # Nginx reverse proxy config
├── deepseek-ocr.service      # Systemd service config
├── .vscode/                  # VSCode debug configurations
├── temp/                     # Temporary files directory

```


### Production Deployment Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Configure proper model paths
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up monitoring and logging
- [ ] Configure automatic backups
- [ ] Implement rate limiting
- [ ] Add API authentication (if needed)
- [ ] Set up log rotation
- [ ] Configure health check alerts

For detailed deployment instructions, see [DEPLOYMENT.md](DEPLOYMENT.md).

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Basic health check |
| GET | `/health` | Detailed health status |
| POST | `/convert` | Upload PDF and start conversion |
| GET | `/status/{task_id}` | Check task status |
| GET | `/download/{task_id}/{file_type}` | Download results |
| DELETE | `/task/{task_id}` | Delete task and files |

### Response Status Codes

- `200` - Success
- `202` - Accepted (processing)
- `400` - Bad request
- `404` - Not found
- `500` - Internal server error
- `503` - Service unavailable

## Performance Tuning

### GPU Memory Issues

If you encounter GPU out-of-memory errors:

```bash
# Reduce these values in .env
MAX_CONCURRENCY=50
MAX_CROPS=4
GPU_MEMORY_UTILIZATION=0.8
```

### Slow Processing

To improve processing speed:

```bash
# Increase worker threads
NUM_WORKERS=128

# Ensure using GPU
CUDA_VISIBLE_DEVICES=0

# Use faster storage (SSD/NVMe)
TEMP_DIR=/fast/storage/path
```

### High Concurrency

For handling many concurrent requests:

```bash
# Increase concurrent tasks
MAX_CONCURRENT_TASKS=16

# Run multiple uvicorn workers
uvicorn app:app --workers 4 --port 8000
```

### Monitoring Performance

```bash
# Monitor GPU usage
watch -n 1 nvidia-smi

# Monitor system resources
htop

# Check task statistics
curl http://localhost:8000/stats  # If implemented
```

## Troubleshooting

### Issue: Model Loading Failed

```bash
# Check model path
ls -la $MODEL_PATH

# Verify tokenizer files exist
ls $MODEL_PATH/tokenizer*

# Check CUDA availability
python -c "import torch; print(torch.cuda.is_available())"
```

### Issue: CUDA Out of Memory

```bash
# Clear GPU memory
nvidia-smi --gpu-reset

# Reduce memory usage (in .env)
MAX_CONCURRENCY=50
GPU_MEMORY_UTILIZATION=0.7
```

### Issue: Port Already in Use

```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port in .env
SERVER_PORT=8001
```

### Issue: Conversion Failed

```bash
# Check task status
curl http://localhost:8000/status/{task_id}

# Check logs
tail -f /tmp/deepseek-ocr-server/app.log

# Verify PDF is valid
file document.pdf
```

### Issue: Slow Startup

Model loading can take 30-60 seconds on first startup. This is normal.

```bash
# Monitor startup progress
docker-compose logs -f deepseek-ocr-server
```

### Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `CUDA not available` | CUDA not installed or detected | Install NVIDIA drivers and CUDA toolkit |
| `Model path not found` | Invalid MODEL_PATH | Check path in .env and verify model files exist |
| `Out of memory` | GPU VRAM exhausted | Reduce MAX_CONCURRENCY or GPU_MEMORY_UTILIZATION |
| `File too large` | Upload exceeds limit | Increase MAX_UPLOAD_SIZE in .env |
| `Task not found` | Invalid task_id or task deleted | Verify task_id from /convert response |

## Performance Benchmarks

Typical performance on NVIDIA A100 (40GB):

- **Single page**: 2-4 seconds
- **10-page document**: 20-40 seconds
- **Concurrent throughput**: 100+ pages/minute
- **GPU utilization**: 80-95%
- **Memory usage**: 6-8GB VRAM

Performance varies based on:
- Document complexity
- Image resolution
- Number of crops
- GPU model and VRAM
- CPU and storage speed

## Security Considerations

### File Upload Security

- Maximum file size is enforced (default 100MB)
- Only PDF files are accepted
- Files are isolated in temporary directories
- Automatic cleanup after processing

### API Security

For production deployment, consider:
- Adding API key authentication
- Implementing rate limiting
- Using HTTPS with valid certificates
- Setting up firewall rules
- Implementing request validation

### Data Privacy

- Temporary files are stored locally
- No data is sent to external services
- Files can be automatically deleted after download
- Configure TEMP_DIR on secure, encrypted storage

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt  # If available

# Run tests before committing
python test_server.py

# Check code style
flake8 app.py pdf_processor.py config.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [DeepSeek OCR](https://github.com/deepseek-ai/DeepSeek-OCR) - Core OCR model
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [vLLM](https://github.com/vllm-project/vllm) - LLM serving engine
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF processing

## Support

- **Documentation**: See [docs/](docs/) directory
- **Issues**: Report bugs via GitHub Issues
- **Questions**: Check existing issues or create a new one

## Changelog

### Version 1.0.0 (2025-10-23)

- Initial release
- PDF to Markdown conversion
- Asynchronous task processing
- Docker support
- Production deployment configurations
- Comprehensive documentation

---

**Built with** [FastAPI](https://fastapi.tiangolo.com/) **and** [DeepSeek OCR](https://github.com/deepseek-ai/DeepSeek-OCR)
