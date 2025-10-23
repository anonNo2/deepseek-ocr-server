#!/usr/bin/env python3
"""
Test client for async PDF conversion API
"""

import requests
import time
import sys
from pathlib import Path


class PDFConversionClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url

    def health_check(self):
        """Check server health"""
        response = requests.get(f"{self.base_url}/health")
        return response.json()

    def get_statistics(self):
        """Get task statistics"""
        response = requests.get(f"{self.base_url}/stats")
        return response.json()

    def convert_pdf(self, pdf_path, prompt=None, skip_repeat=True, crop_mode=True):
        """Submit PDF for conversion"""
        with open(pdf_path, 'rb') as f:
            files = {'file': (Path(pdf_path).name, f, 'application/pdf')}
            data = {
                'skip_repeat': skip_repeat,
                'crop_mode': crop_mode
            }
            if prompt:
                data['prompt'] = prompt

            response = requests.post(f"{self.base_url}/convert", files=files, data=data)
            return response.json()

    def get_status(self, task_id):
        """Get task status"""
        response = requests.get(f"{self.base_url}/status/{task_id}")
        return response.json()

    def download_file(self, task_id, file_type="markdown"):
        """Download converted file"""
        response = requests.get(f"{self.base_url}/download/{task_id}/{file_type}")
        if response.status_code == 200:
            return response.content
        else:
            return None

    def wait_for_completion(self, task_id, poll_interval=2, max_wait=600):
        """Wait for task to complete"""
        start_time = time.time()

        while time.time() - start_time < max_wait:
            status = self.get_status(task_id)
            print(f"Task {task_id}: {status['status']} - {status.get('message', '')}", end='')

            if status.get('queue_position'):
                print(f" (Queue position: {status['queue_position']})")
            else:
                print()

            if status['status'] == 'completed':
                return True, status
            elif status['status'] == 'failed':
                return False, status

            time.sleep(poll_interval)

        return False, {"error": "Timeout waiting for completion"}


def test_single_conversion(client, pdf_path):
    """Test single PDF conversion"""
    print("\n=== Testing Single PDF Conversion ===")

    # Submit conversion
    result = client.convert_pdf(pdf_path)
    task_id = result['task_id']
    print(f"Task submitted: {task_id}")
    print(f"Status: {result['status']}")

    # Wait for completion
    success, final_status = client.wait_for_completion(task_id)

    if success:
        print(f"✓ Conversion completed successfully!")
        print(f"Output file: {final_status.get('output_file')}")
    else:
        print(f"✗ Conversion failed: {final_status.get('error')}")


def test_concurrent_conversions(client, pdf_path, num_tasks=10):
    """Test concurrent PDF conversions"""
    print(f"\n=== Testing {num_tasks} Concurrent PDF Conversions ===")

    # Check max concurrent tasks
    health = client.health_check()
    max_concurrent = health.get('max_concurrent_tasks', 8)
    print(f"Server max concurrent tasks: {max_concurrent}")

    # Submit multiple tasks
    task_ids = []
    print(f"\nSubmitting {num_tasks} tasks...")
    for i in range(num_tasks):
        result = client.convert_pdf(pdf_path)
        task_ids.append(result['task_id'])
        print(f"Task {i+1}/{num_tasks} submitted: {result['task_id']}")
        time.sleep(0.1)  # Small delay to avoid overwhelming the server

    # Monitor all tasks
    print("\nMonitoring task progress...")
    completed = 0
    failed = 0

    while completed + failed < num_tasks:
        stats = client.get_statistics()
        print(f"\rQueued: {stats['statistics']['queued']}, "
              f"Processing: {stats['statistics']['processing']}, "
              f"Completed: {stats['statistics']['completed']}, "
              f"Failed: {stats['statistics']['failed']}", end='')

        # Check individual task statuses
        for task_id in task_ids:
            status = client.get_status(task_id)
            if status['status'] == 'completed' and task_id not in [tid for tid in task_ids[:completed]]:
                completed += 1
            elif status['status'] == 'failed' and task_id not in [tid for tid in task_ids[:completed+failed]]:
                failed += 1

        time.sleep(1)

    print(f"\n✓ All tasks completed: {completed} successful, {failed} failed")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_async_client.py <pdf_file> [num_concurrent_tests]")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not Path(pdf_path).exists():
        print(f"Error: PDF file not found: {pdf_path}")
        sys.exit(1)

    num_concurrent = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    client = PDFConversionClient()

    # Health check
    print("=== Health Check ===")
    health = client.health_check()
    print(f"Status: {health['status']}")
    print(f"Processor loaded: {health['processor_loaded']}")
    print(f"Max concurrent tasks: {health.get('max_concurrent_tasks', 'N/A')}")

    # Test single conversion
    test_single_conversion(client, pdf_path)

    # Test concurrent conversions
    test_concurrent_conversions(client, pdf_path, num_concurrent)


if __name__ == "__main__":
    main()
