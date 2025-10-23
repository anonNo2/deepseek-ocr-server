import os
from pathlib import Path
from transformers import AutoTokenizer

class ModelConfig:
    """Model configuration"""

    # Model path - change this to your model path
    MODEL_PATH = os.getenv(
        'MODEL_PATH',
        '/data/wuxiangbo/util_models/DeepSeek-OCR'
    )

    # CUDA settings
    CUDA_VISIBLE_DEVICES = os.getenv('CUDA_VISIBLE_DEVICES', '0')

    # Model settings
    MAX_CONCURRENCY = int(os.getenv('MAX_CONCURRENCY', '100'))
    NUM_WORKERS = int(os.getenv('NUM_WORKERS', '64'))
    GPU_MEMORY_UTILIZATION = float(os.getenv('GPU_MEMORY_UTILIZATION', '0.9'))

    # Image processing settings
    BASE_SIZE = int(os.getenv('BASE_SIZE', '1024'))
    IMAGE_SIZE = int(os.getenv('IMAGE_SIZE', '640'))
    CROP_MODE = os.getenv('CROP_MODE', 'True').lower() == 'true'
    MIN_CROPS = int(os.getenv('MIN_CROPS', '2'))
    MAX_CROPS = int(os.getenv('MAX_CROPS', '6'))
    PRINT_NUM_VIS_TOKENS = os.getenv('PRINT_NUM_VIS_TOKENS', 'False').lower() == 'true'

    # Processing settings
    SKIP_REPEAT = os.getenv('SKIP_REPEAT', 'True').lower() == 'true'

    # Default prompt
    DEFAULT_PROMPT = os.getenv(
        'DEFAULT_PROMPT',
        '<image>\n<|grounding|>Convert the document to markdown.'
    )
    
    TOKENIZER = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)


class ServerConfig:
    """Server configuration"""

    # Server settings
    HOST = os.getenv('SERVER_HOST', '0.0.0.0')
    PORT = int(os.getenv('SERVER_PORT', '8000'))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Temporary directory for file storage
    TEMP_DIR = Path(os.getenv('TEMP_DIR', '/tmp/deepseek-ocr-server'))

    # Maximum upload file size (100MB)
    MAX_UPLOAD_SIZE = int(os.getenv('MAX_UPLOAD_SIZE', 100 * 1024 * 1024))

    # Maximum concurrent PDF processing tasks
    MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', '8'))
