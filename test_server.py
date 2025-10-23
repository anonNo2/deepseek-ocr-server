#!/usr/bin/env python3
"""
Test script for DeepSeek OCR Server
"""

import os
import sys
import time
import requests
from pathlib import Path


class Colors:
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    RESET = '\033[0m'


def print_colored(text, color):
    print(f"{color}{text}{Colors.RESET}")


def test_health_check(base_url):
    """Test health check endpoint"""
    print_colored("\n=== Testing Health Check ===", Colors.BLUE)
    try:
        response = requests.get(f"{base_url}/health")
        response.raise_for_status()
        print_colored(f"✓ Health check passed: {response.json()}", Colors.GREEN)
        return True
    except Exception as e:
        print_colored(f"✗ Health check failed: {e}", Colors.RED)
        return False


def test_convert_pdf(base_url, pdf_path):
    """Test PDF conversion"""
    print_colored(f"\n=== Testing PDF Conversion ===", Colors.BLUE)
    print(f"PDF file: {pdf_path}")

    if not os.path.exists(pdf_path):
        print_colored(f"✗ PDF file not found: {pdf_path}", Colors.RED)
        return None

    try:
        # Upload PDF
        with open(pdf_path, 'rb') as f:
            files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
            data = {
                'skip_repeat': 'true',
                'crop_mode': 'true'
            }
            response = requests.post(f"{base_url}/convert", files=files, data=data)
            response.raise_for_status()

        result = response.json()
        task_id = result['task_id']
        print_colored(f"✓ PDF uploaded successfully", Colors.GREEN)
        print(f"Task ID: {task_id}")
        print(f"Status: {result['status']}")

        return task_id

    except Exception as e:
        print_colored(f"✗ PDF conversion failed: {e}", Colors.RED)
        return None


def test_check_status(base_url, task_id, max_wait=300):
    """Test status check and wait for completion"""
    print_colored(f"\n=== Checking Task Status ===", Colors.BLUE)
    print(f"Task ID: {task_id}")

    start_time = time.time()
    while True:
        try:
            response = requests.get(f"{base_url}/status/{task_id}")
            response.raise_for_status()

            result = response.json()
            status = result['status']
            elapsed = int(time.time() - start_time)

            print(f"\rStatus: {status} (elapsed: {elapsed}s)", end='', flush=True)

            if status == 'completed':
                print()
                print_colored(f"✓ Task completed successfully", Colors.GREEN)
                print(f"Message: {result.get('message')}")
                return True
            elif status == 'failed':
                print()
                print_colored(f"✗ Task failed", Colors.RED)
                print(f"Error: {result.get('error')}")
                return False
            elif status == 'processing':
                if elapsed > max_wait:
                    print()
                    print_colored(f"✗ Timeout after {max_wait}s", Colors.YELLOW)
                    return False
                time.sleep(2)
            else:
                print()
                print_colored(f"? Unknown status: {status}", Colors.YELLOW)
                return False

        except Exception as e:
            print()
            print_colored(f"✗ Status check failed: {e}", Colors.RED)
            return False


def test_download_files(base_url, task_id, output_dir):
    """Test file downloads"""
    print_colored(f"\n=== Testing File Downloads ===", Colors.BLUE)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_types = [
        ('markdown', 'output.mmd'),
        ('markdown_det', 'output_det.mmd'),
        ('pdf_layout', 'output_layouts.pdf'),
        ('images_zip', 'images.zip')
    ]

    success_count = 0
    for file_type, filename in file_types:
        try:
            response = requests.get(f"{base_url}/download/{task_id}/{file_type}")
            response.raise_for_status()

            file_path = output_path / filename
            with open(file_path, 'wb') as f:
                f.write(response.content)

            file_size = os.path.getsize(file_path)
            print_colored(f"✓ Downloaded {file_type}: {filename} ({file_size} bytes)", Colors.GREEN)
            success_count += 1

        except Exception as e:
            print_colored(f"✗ Failed to download {file_type}: {e}", Colors.RED)

    return success_count == len(file_types)


def main():
    # Configuration
    BASE_URL = os.getenv('SERVER_URL', 'http://localhost:8000')
    PDF_PATH = os.getenv('TEST_PDF_PATH', '../demo_input/成人糖尿病食养指南(2023年版).pdf')
    OUTPUT_DIR = os.getenv('TEST_OUTPUT_DIR', './test_output')

    print_colored("=" * 60, Colors.BLUE)
    print_colored("DeepSeek OCR Server Test Suite", Colors.BLUE)
    print_colored("=" * 60, Colors.BLUE)
    print(f"Server URL: {BASE_URL}")
    print(f"Test PDF: {PDF_PATH}")
    print(f"Output Directory: {OUTPUT_DIR}")

    # Test 1: Health Check
    if not test_health_check(BASE_URL):
        print_colored("\n✗ Server is not healthy. Please start the server first.", Colors.RED)
        sys.exit(1)

    # Test 2: Convert PDF
    task_id = test_convert_pdf(BASE_URL, PDF_PATH)
    if not task_id:
        print_colored("\n✗ PDF conversion failed", Colors.RED)
        sys.exit(1)

    # Test 3: Check Status
    if not test_check_status(BASE_URL, task_id, max_wait=300):
        print_colored("\n✗ Task did not complete successfully", Colors.RED)
        sys.exit(1)

    # Test 4: Download Files
    if not test_download_files(BASE_URL, task_id, OUTPUT_DIR):
        print_colored("\n⚠ Some downloads failed", Colors.YELLOW)

    print_colored("\n" + "=" * 60, Colors.BLUE)
    print_colored("All Tests Completed!", Colors.GREEN)
    print_colored("=" * 60, Colors.BLUE)
    print(f"\nOutput files saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
