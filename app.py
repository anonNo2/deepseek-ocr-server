import os
import io
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import Optional, Literal
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import uvicorn
from contextlib import asynccontextmanager

from pdf_processor import PDFProcessor
from config import ServerConfig

# Global processor instance
processor: Optional[PDFProcessor] = None

# Semaphore for limiting concurrent tasks
task_semaphore: Optional[asyncio.Semaphore] = None

# Task statistics
task_stats = {
    "total": 0,
    "queued": 0,
    "processing": 0,
    "completed": 0,
    "failed": 0
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global processor, task_semaphore

    # Startup: Initialize the PDF processor
    print("Initializing PDF Processor...")
    processor = PDFProcessor()
    print("PDF Processor initialized successfully")

    # Initialize semaphore for task concurrency control
    task_semaphore = asyncio.Semaphore(ServerConfig.MAX_CONCURRENT_TASKS)
    print(f"Task semaphore initialized with max concurrent tasks: {ServerConfig.MAX_CONCURRENT_TASKS}")

    yield

    # Shutdown: Clean up resources
    print("Shutting down PDF Processor...")
    if processor:
        processor.cleanup()


app = FastAPI(
    title="DeepSeek OCR PDF to Markdown Service",
    description="Convert PDF documents to Markdown using DeepSeek OCR",
    version="1.0.0",
    lifespan=lifespan
) 


class ConversionStatus(BaseModel):
    task_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    message: Optional[str] = None
    output_file: Optional[str] = None
    error: Optional[str] = None
    queue_position: Optional[int] = None  # Position in queue if queued


# Store task status
task_status = {}


def cleanup_task_files(task_id: str):
    """Clean up task files after download"""
    task_dir = ServerConfig.TEMP_DIR / task_id
    if task_dir.exists():
        shutil.rmtree(task_dir)
    if task_id in task_status:
        del task_status[task_id]


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "service": "DeepSeek OCR PDF to Markdown",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with task statistics"""
    return {
        "status": "healthy",
        "processor_loaded": processor is not None,
        "max_concurrent_tasks": ServerConfig.MAX_CONCURRENT_TASKS,
        "task_stats": task_stats
    }


@app.post("/convert", response_model=ConversionStatus)
async def convert_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    prompt: Optional[str] = None,
    skip_repeat: bool = True,
    crop_mode: bool = True
):
    """
    Convert PDF to Markdown

    Parameters:
    - file: PDF file to convert
    - prompt: Custom prompt for OCR (optional)
    - skip_repeat: Skip pages without EOS token (default: True)
    - crop_mode: Enable crop mode for better performance (default: True)

    Returns task_id immediately and processes in background
    """

    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    # Generate unique task ID
    task_id = str(uuid.uuid4())
    task_dir = ServerConfig.TEMP_DIR / task_id
    task_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    input_path = task_dir / file.filename
    try:
        contents = await file.read()
        with open(input_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Initialize task status as queued
    task_status[task_id] = {
        "status": "queued",
        "message": "Task queued, waiting for processing slot",
        "created_at": asyncio.get_event_loop().time()
    }

    # Update statistics
    task_stats["total"] += 1
    task_stats["queued"] += 1

    # Process PDF in background with semaphore control
    background_tasks.add_task(
        process_pdf_task_wrapper,
        task_id,
        str(input_path),
        str(task_dir),
        prompt,
        skip_repeat,
        crop_mode
    )

    return ConversionStatus(
        task_id=task_id,
        status="queued",
        message="Task queued successfully",
        queue_position=task_stats["queued"]
    )


async def process_pdf_task_wrapper(
    task_id: str,
    input_path: str,
    output_dir: str,
    prompt: Optional[str],
    skip_repeat: bool,
    crop_mode: bool
):
    """Wrapper for PDF processing task with semaphore control"""
    # Wait for available slot
    async with task_semaphore:
        # Update status to processing
        if task_id in task_status:
            task_status[task_id]["status"] = "processing"
            task_status[task_id]["message"] = "PDF conversion in progress"
            task_stats["queued"] -= 1
            task_stats["processing"] += 1

        # Process the PDF
        await process_pdf_task(
            task_id,
            input_path,
            output_dir,
            prompt,
            skip_repeat,
            crop_mode
        )


async def process_pdf_task(
    task_id: str,
    input_path: str,
    output_dir: str,
    prompt: Optional[str],
    skip_repeat: bool,
    crop_mode: bool
):
    """Background task to process PDF"""
    try:
        # Run the synchronous processor in a thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: processor.process_pdf(
                input_path=input_path,
                output_dir=output_dir,
                prompt=prompt,
                skip_repeat=skip_repeat,
                crop_mode=crop_mode
            )
        )

        task_status[task_id] = {
            "status": "completed",
            "message": "PDF converted successfully",
            "output_file": result["markdown_file"],
            "markdown_det_file": result["markdown_det_file"],
            "pdf_layout_file": result["pdf_layout_file"],
            "images_dir": result["images_dir"]
        }

        # Update statistics
        task_stats["processing"] -= 1
        task_stats["completed"] += 1

    except Exception as e:
        task_status[task_id] = {
            "status": "failed",
            "error": str(e),
            "message": "PDF conversion failed"
        }

        # Update statistics
        task_stats["processing"] -= 1
        task_stats["failed"] += 1


@app.get("/status/{task_id}", response_model=ConversionStatus)
async def get_status(task_id: str):
    """Get conversion task status"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    status = task_status[task_id]

    # Calculate queue position if still queued
    queue_position = None
    if status["status"] == "queued":
        # Count tasks that were created before this one and are still queued
        queue_position = sum(
            1 for tid, s in task_status.items()
            if s["status"] == "queued" and s.get("created_at", 0) <= status.get("created_at", 0)
        )

    return ConversionStatus(
        task_id=task_id,
        status=status["status"],
        message=status.get("message"),
        output_file=status.get("output_file"),
        error=status.get("error"),
        queue_position=queue_position
    )


@app.get("/stats")
async def get_statistics():
    """Get task processing statistics"""
    return {
        "max_concurrent_tasks": ServerConfig.MAX_CONCURRENT_TASKS,
        "statistics": task_stats,
        "active_tasks": {
            "queued": [tid for tid, s in task_status.items() if s["status"] == "queued"],
            "processing": [tid for tid, s in task_status.items() if s["status"] == "processing"]
        }
    }


@app.get("/download/{task_id}/{file_type}")
async def download_file(task_id: str, file_type: str, background_tasks: BackgroundTasks):
    """
    Download converted files

    file_type: markdown | markdown_det | pdf_layout | images_zip
    """
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    status = task_status[task_id]
    if status["status"] != "completed":
        raise HTTPException(status_code=400, detail="Task not completed yet")

    task_dir = ServerConfig.TEMP_DIR / task_id

    try:
        if file_type == "markdown":
            file_path = status["output_file"]
            media_type = "text/markdown"
        elif file_type == "markdown_det":
            file_path = status["markdown_det_file"]
            media_type = "text/markdown"
        elif file_type == "pdf_layout":
            file_path = status["pdf_layout_file"]
            media_type = "application/pdf"
        elif file_type == "images_zip":
            # Create zip of images directory
            import zipfile
            images_dir = Path(status["images_dir"])
            zip_path = task_dir / "images.zip"

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in images_dir.glob("*"):
                    if file.is_file():
                        zipf.write(file, file.name)

            file_path = str(zip_path)
            media_type = "application/zip"
        else:
            raise HTTPException(status_code=400, detail="Invalid file type")

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")

        # Schedule cleanup after download
        # background_tasks.add_task(cleanup_task_files, task_id)

        return FileResponse(
            path=file_path,
            media_type=media_type,
            filename=os.path.basename(file_path)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download file: {str(e)}")


@app.delete("/task/{task_id}")
async def delete_task(task_id: str):
    """Delete task and cleanup files"""
    if task_id not in task_status:
        raise HTTPException(status_code=404, detail="Task not found")

    cleanup_task_files(task_id)

    return {"message": f"Task {task_id} deleted successfully"}


if __name__ == "__main__":
    # Ensure temp directory exists
    ServerConfig.TEMP_DIR.mkdir(parents=True, exist_ok=True)

    uvicorn.run(
        "app:app",
        host=ServerConfig.HOST,
        port=ServerConfig.PORT,
        reload=ServerConfig.DEBUG,
        workers=1  # Must be 1 to share the loaded model
    )
