# DeepSeek OCR 服务器

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.5-green.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)

一个生产就绪的 FastAPI 服务，使用 DeepSeek OCR 和 GPU 加速将 PDF 文档转换为 Markdown。

[English](README.md) | [简体中文](README_CN.md)

## 功能特性

- **PDF 转 Markdown** - 高质量的文档转换与 OCR 识别
- **异步处理** - 非阻塞任务队列，支持状态跟踪
- **RESTful API** - 简洁、文档完善的 API 接口
- **GPU 加速** - CUDA 优化，高性能处理
- **布局保持** - 保留文档结构和格式
- **边界框可视化** - 检测元素的可视化表示
- **图片提取** - 从文档中提取并保存图片
- **Docker 支持** - 使用 Docker Compose 容器化部署
- **生产就绪** - Nginx 配置、systemd 服务和健康检查

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [安装部署](#安装部署)
  - [本地安装](#本地安装)
  - [Docker 安装](#docker-安装)
- [API 使用](#api-使用)
- [配置说明](#配置说明)
- [开发指南](#开发指南)
- [生产部署](#生产部署)
- [API 文档](#api-文档)
- [性能调优](#性能调优)
- [故障排查](#故障排查)
- [贡献指南](#贡献指南)
- [开源协议](#开源协议)

## 系统要求

- **Python**: 3.10 或更高版本
- **GPU**: 支持 CUDA 的 NVIDIA GPU（推荐）
- **CUDA**: 11.8 或更高版本
- **内存**: 16GB+ 系统内存，8GB+ GPU 显存
- **存储**: 20GB+ 用于模型和临时文件
- **操作系统**: Linux（推荐 Ubuntu 22.04+）

## 快速开始

### 使用 Docker（推荐）

```bash
# 1. 进入项目目录
cd deepseek-ocr-server

# 2. 构建并启动服务
docker-compose up -d

# 3. 健康检查
curl http://localhost:8000/health

# 4. 转换 PDF
curl -X POST http://localhost:8000/convert \
  -F "file=@document.pdf" \
  -F "skip_repeat=true" \
  -F "crop_mode=true"
```

### 使用 Python

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境
cp .env.example .env
# 编辑 .env 文件设置参数

# 3. 启动服务器
python app.py
```

## 安装部署

### 本地安装

#### 1. 环境准备

确保已安装 CUDA 和 Python：

```bash
# 检查 CUDA
nvidia-smi

# 检查 Python
python3 --version
```

#### 2. 克隆和配置

```bash
# 进入项目目录
cd deepseek-ocr-server

# 运行自动安装脚本（复制 DeepSeek 模块）
bash setup.sh

# 安装 Python 依赖
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置（必需）
nano .env
```

关键配置项：

```bash
MODEL_PATH=/path/to/DeepSeek-OCR  # DeepSeek OCR 模型路径
CUDA_VISIBLE_DEVICES=0             # GPU 设备 ID
SERVER_PORT=8000                   # API 服务器端口
```

#### 4. 启动服务器

```bash
# 开发模式（支持热重载）
python app.py

# 生产模式（使用 uvicorn）
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
```

### Docker 安装

#### 1. 构建镜像

```bash
# 构建 Docker 镜像
docker build -t deepseek-ocr-server:0.1 .
```

#### 2. 配置 Docker Compose

编辑 `docker-compose.yml` 设置模型路径：

```yaml
volumes:
  - /path/to/your/DeepSeek-OCR:/models:ro
```

#### 3. 启动服务

```bash
# 后台启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## API 使用

### 健康检查

```bash
curl http://localhost:8000/health
```

响应：
```json
{
  "status": "healthy",
  "processor_loaded": true,
  "version": "1.0.0"
}
```

### 转换 PDF

```bash
curl -X POST http://localhost:8000/convert \
  -F "file=@document.pdf" \
  -F "prompt=<image>\n<|grounding|>Convert the document to markdown." \
  -F "skip_repeat=true" \
  -F "crop_mode=true"
```

响应：
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "message": "PDF conversion started"
}
```

### 查询任务状态

```bash
curl http://localhost:8000/status/{task_id}
```

响应：
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

### 下载结果

```bash
# 下载 markdown 文件
curl http://localhost:8000/download/{task_id}/markdown -o output.mmd

# 下载带检测信息的 markdown
curl http://localhost:8000/download/{task_id}/markdown_det -o output_det.mmd

# 下载带布局标注的 PDF
curl http://localhost:8000/download/{task_id}/pdf_layout -o output_layouts.pdf

# 下载提取的图片压缩包
curl http://localhost:8000/download/{task_id}/images_zip -o images.zip
```

### 删除任务

```bash
curl -X DELETE http://localhost:8000/task/{task_id}
```

### 使用 Python 客户端

```python
import requests

# 上传 PDF
with open('document.pdf', 'rb') as f:
    files = {'file': f}
    data = {'skip_repeat': 'true', 'crop_mode': 'true'}
    response = requests.post('http://localhost:8000/convert', files=files, data=data)
    task_id = response.json()['task_id']

# 检查状态
status = requests.get(f'http://localhost:8000/status/{task_id}').json()
print(f"状态: {status['status']}")

# 下载结果
if status['status'] == 'completed':
    result = requests.get(f'http://localhost:8000/download/{task_id}/markdown')
    with open('output.mmd', 'wb') as f:
        f.write(result.content)
```

### 使用提供的客户端脚本

```bash
python api_client.py document.pdf
```

## 配置说明

### 环境变量

服务通过 `.env` 文件进行配置：

#### 模型配置

```bash
MODEL_PATH=/data/models/DeepSeek-OCR  # DeepSeek OCR 模型权重路径
CUDA_VISIBLE_DEVICES=0                 # GPU 设备 ID（逗号分隔）
```

#### 性能设置

```bash
MAX_CONCURRENCY=100                    # 最大并发 OCR 操作数
NUM_WORKERS=64                         # 图像预处理工作线程数
GPU_MEMORY_UTILIZATION=0.9             # GPU 内存使用率（0.0-1.0）
MAX_CONCURRENT_TASKS=8                 # 最大并行 PDF 处理任务数
```

#### 图像处理

```bash
BASE_SIZE=1024                         # 处理基础图像大小
IMAGE_SIZE=640                         # 目标图像大小
CROP_MODE=True                         # 启用裁剪模式以提高准确性
MIN_CROPS=2                            # 每张图片最小裁剪数
MAX_CROPS=6                            # 每张图片最大裁剪数
SKIP_REPEAT=True                       # 跳过没有 EOS token 的页面
```

#### 服务器设置

```bash
SERVER_HOST=0.0.0.0                    # 服务器绑定地址
SERVER_PORT=8000                       # 服务器端口
DEBUG=False                            # 调试模式（True/False）
TEMP_DIR=/tmp/deepseek-ocr-server      # 临时文件目录
MAX_UPLOAD_SIZE=104857600              # 最大上传大小（字节，默认 100MB）
```

#### 默认提示词

```bash
DEFAULT_PROMPT="<image>\n<|grounding|>Convert the document to markdown."
```

### 通过 Docker 配置

在 `docker-compose.yml` 中覆盖环境变量：

```yaml
environment:
  - MODEL_PATH=/models
  - CUDA_VISIBLE_DEVICES=0
  - MAX_CONCURRENCY=100
  - DEBUG=False
```

## 开发指南

### VSCode 调试

项目包含 VSCode 调试配置，按 `F5` 启动调试。

可用配置：
- **Python: FastAPI Server** - 开发模式，支持自动重载
- **Python: FastAPI Server (No Reload)** - 稳定调试，不重载
- **Python: Current File** - 调试当前打开的文件

### 运行测试

```bash
# 运行测试套件
python test_server.py

# 测试异步客户端
python test_async_client.py
```

### 使用 Makefile

```bash
# 启动服务器
make start

# 运行测试
make test

# 清理临时文件
make clean

# 构建 Docker 镜像
make build

# 查看所有命令
make help
```

### 项目结构

```
deepseek-ocr-server/
├── app.py                    # FastAPI 应用程序
├── pdf_processor.py          # PDF 处理逻辑
├── config.py                 # 配置管理
├── deepseek_ocr.py           # DeepSeek OCR 模型接口
├── deepencoder/              # 模型编码器模块
├── process/                  # 图像处理工具
├── api_client.py             # Python API 客户端
├── test_server.py            # 测试套件
├── requirements.txt          # Python 依赖
├── .env.example              # 环境变量模板
├── Dockerfile                # Docker 镜像定义
├── docker-compose.yml        # Docker Compose 配置
├── setup.sh                  # 安装脚本
├── start_server.sh           # 服务器启动脚本
├── Makefile                  # 常用命令
├── nginx.conf                # Nginx 反向代理配置
├── deepseek-ocr.service      # Systemd 服务配置
├── .vscode/                  # VSCode 调试配置
├── temp/                     # 临时文件目录
└── docs/
    ├── QUICKSTART.md         # 快速开始指南
    ├── DEPLOYMENT.md         # 部署指南
    └── PROJECT_SUMMARY.md    # 项目总结
```

## 生产部署

### 使用 Systemd

```bash
# 复制服务文件
sudo cp deepseek-ocr.service /etc/systemd/system/

# 编辑服务文件中的路径
sudo nano /etc/systemd/system/deepseek-ocr.service

# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable deepseek-ocr
sudo systemctl start deepseek-ocr

# 检查状态
sudo systemctl status deepseek-ocr

# 查看日志
journalctl -u deepseek-ocr -f
```

### 使用 Nginx 反向代理

```bash
# 复制 nginx 配置
sudo cp nginx.conf /etc/nginx/sites-available/deepseek-ocr

# 创建符号链接
sudo ln -s /etc/nginx/sites-available/deepseek-ocr /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重载 nginx
sudo systemctl reload nginx
```

### 生产部署检查清单

- [ ] 在 `.env` 中设置 `DEBUG=False`
- [ ] 配置正确的模型路径
- [ ] 设置 SSL/TLS 证书
- [ ] 配置防火墙规则
- [ ] 设置监控和日志
- [ ] 配置自动备份
- [ ] 实施速率限制
- [ ] 添加 API 认证（如需要）
- [ ] 设置日志轮转
- [ ] 配置健康检查告警

详细部署说明请参阅 [DEPLOYMENT.md](DEPLOYMENT.md)。

## API 文档

服务启动后，访问：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### API 端点

| 方法 | 端点 | 描述 |
|--------|----------|-------------|
| GET | `/` | 基础健康检查 |
| GET | `/health` | 详细健康状态 |
| POST | `/convert` | 上传 PDF 并开始转换 |
| GET | `/status/{task_id}` | 检查任务状态 |
| GET | `/download/{task_id}/{file_type}` | 下载结果 |
| DELETE | `/task/{task_id}` | 删除任务和文件 |

### 响应状态码

- `200` - 成功
- `202` - 已接受（处理中）
- `400` - 错误请求
- `404` - 未找到
- `500` - 内部服务器错误
- `503` - 服务不可用

## 性能调优

### GPU 内存问题

如果遇到 GPU 内存不足错误：

```bash
# 在 .env 中减少这些值
MAX_CONCURRENCY=50
MAX_CROPS=4
GPU_MEMORY_UTILIZATION=0.8
```

### 处理速度慢

提高处理速度：

```bash
# 增加工作线程
NUM_WORKERS=128

# 确保使用 GPU
CUDA_VISIBLE_DEVICES=0

# 使用更快的存储（SSD/NVMe）
TEMP_DIR=/fast/storage/path
```

### 高并发

处理大量并发请求：

```bash
# 增加并发任务数
MAX_CONCURRENT_TASKS=16

# 运行多个 uvicorn worker
uvicorn app:app --workers 4 --port 8000
```

### 性能监控

```bash
# 监控 GPU 使用情况
watch -n 1 nvidia-smi

# 监控系统资源
htop

# 检查任务统计（如已实现）
curl http://localhost:8000/stats
```

## 故障排查

### 问题：模型加载失败

```bash
# 检查模型路径
ls -la $MODEL_PATH

# 验证 tokenizer 文件存在
ls $MODEL_PATH/tokenizer*

# 检查 CUDA 可用性
python -c "import torch; print(torch.cuda.is_available())"
```

### 问题：CUDA 内存不足

```bash
# 清除 GPU 内存
nvidia-smi --gpu-reset

# 减少内存使用（在 .env 中）
MAX_CONCURRENCY=50
GPU_MEMORY_UTILIZATION=0.7
```

### 问题：端口已被占用

```bash
# 查找占用端口的进程
lsof -i :8000

# 终止进程
kill -9 <PID>

# 或在 .env 中更改端口
SERVER_PORT=8001
```

### 问题：转换失败

```bash
# 检查任务状态
curl http://localhost:8000/status/{task_id}

# 检查日志
tail -f /tmp/deepseek-ocr-server/app.log

# 验证 PDF 有效
file document.pdf
```

### 问题：启动缓慢

首次启动时模型加载可能需要 30-60 秒，这是正常的。

```bash
# 监控启动进度
docker-compose logs -f deepseek-ocr-server
```

### 常见错误消息

| 错误 | 原因 | 解决方案 |
|-------|-------|----------|
| `CUDA not available` | CUDA 未安装或未检测到 | 安装 NVIDIA 驱动和 CUDA 工具包 |
| `Model path not found` | MODEL_PATH 无效 | 检查 .env 中的路径并验证模型文件存在 |
| `Out of memory` | GPU 显存耗尽 | 减少 MAX_CONCURRENCY 或 GPU_MEMORY_UTILIZATION |
| `File too large` | 上传超出限制 | 在 .env 中增加 MAX_UPLOAD_SIZE |
| `Task not found` | task_id 无效或任务已删除 | 验证来自 /convert 响应的 task_id |

## 性能基准

在 NVIDIA A100 (40GB) 上的典型性能：

- **单页**: 2-4 秒
- **10 页文档**: 20-40 秒
- **并发吞吐量**: 100+ 页/分钟
- **GPU 利用率**: 80-95%
- **内存使用**: 6-8GB 显存

性能因以下因素而异：
- 文档复杂度
- 图像分辨率
- 裁剪数量
- GPU 型号和显存
- CPU 和存储速度

## 安全注意事项

### 文件上传安全

- 强制执行最大文件大小（默认 100MB）
- 仅接受 PDF 文件
- 文件隔离在临时目录
- 处理后自动清理

### API 安全

生产部署时，建议：
- 添加 API 密钥认证
- 实施速率限制
- 使用有效证书的 HTTPS
- 设置防火墙规则
- 实施请求验证

### 数据隐私

- 临时文件存储在本地
- 不向外部服务发送数据
- 下载后可自动删除文件
- 在安全的加密存储上配置 TEMP_DIR

## 贡献指南

欢迎贡献！请遵循以下指南：

1. Fork 仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 开启 Pull Request

### 开发环境设置

```bash
# 安装开发依赖（如可用）
pip install -r requirements-dev.txt

# 提交前运行测试
python test_server.py

# 检查代码风格
flake8 app.py pdf_processor.py config.py
```

## 开源协议

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 致谢

- [DeepSeek OCR](https://github.com/deepseek-ai/DeepSeek-OCR) - 核心 OCR 模型
- [FastAPI](https://fastapi.tiangolo.com/) - Web 框架
- [vLLM](https://github.com/vllm-project/vllm) - LLM 服务引擎
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF 处理

## 支持

- **文档**: 参见 [docs/](docs/) 目录
- **问题**: 通过 GitHub Issues 报告 bug
- **提问**: 查看现有 issues 或创建新 issue

## 更新日志

### 版本 1.0.0 (2025-10-23)

- 初始版本发布
- PDF 转 Markdown 转换
- 异步任务处理
- Docker 支持
- 生产部署配置
- 完善的文档

---

**基于** [FastAPI](https://fastapi.tiangolo.com/) **和** [DeepSeek OCR](https://github.com/deepseek-ai/DeepSeek-OCR) **构建**
