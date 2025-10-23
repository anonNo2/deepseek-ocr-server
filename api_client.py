#!/usr/bin/env python3
"""
Simple API client for testing DeepSeek OCR Server
"""

import os
import sys
import time
import requests
from pathlib import Path


def simple_convert(pdf_path, server_url="http://localhost:8000", output_dir="./output"):
    """
    Simple function to convert PDF to Markdown

    Args:
        pdf_path: Path to PDF file
        server_url: Server URL (default: http://localhost:8000)
        output_dir: Output directory for results

    Returns:
        dict with output file paths
    """

    print(f"Converting PDF: {pdf_path}")
    print(f"Server: {server_url}")

    # Step 1: Upload and start conversion
    print("\n[1/3] Uploading PDF...")

    with open(pdf_path, 'rb') as f:
        files = {'file': (os.path.basename(pdf_path), f, 'application/pdf')}
        data = {
            'skip_repeat': 'true',
            'crop_mode': 'true'
        }

        try:
            response = requests.post(f"{server_url}/convert", files=files, data=data)
            response.raise_for_status()
            result = response.json()
            task_id = result['task_id']
            print(f"✓ Task created: {task_id}")
        except Exception as e:
            print(f"✗ Upload failed: {e}")
            return None

    # Step 2: Wait for completion
    print("\n[2/3] Processing...")

    while True:
        try:
            response = requests.get(f"{server_url}/status/{task_id}")
            response.raise_for_status()
            status_data = response.json()
            status = status_data['status']

            if status == 'completed':
                print("✓ Processing completed!")
                break
            elif status == 'failed':
                print(f"✗ Processing failed: {status_data.get('error')}")
                return None
            elif status == 'processing':
                print(".", end='', flush=True)
                time.sleep(2)
            else:
                print(f"? Unknown status: {status}")
                return None

        except Exception as e:
            print(f"\n✗ Status check failed: {e}")
            return None

    # Step 3: Download results
    print("\n[3/3] Downloading results...")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {}

    # Download markdown
    try:
        response = requests.get(f"{server_url}/download/{task_id}/markdown")
        response.raise_for_status()
        markdown_path = output_path / f"{Path(pdf_path).stem}.mmd"
        with open(markdown_path, 'wb') as f:
            f.write(response.content)
        results['markdown'] = str(markdown_path)
        print(f"✓ Markdown: {markdown_path}")
    except Exception as e:
        print(f"✗ Failed to download markdown: {e}")

    # Download markdown with detections
    try:
        response = requests.get(f"{server_url}/download/{task_id}/markdown_det")
        response.raise_for_status()
        markdown_det_path = output_path / f"{Path(pdf_path).stem}_det.mmd"
        with open(markdown_det_path, 'wb') as f:
            f.write(response.content)
        results['markdown_det'] = str(markdown_det_path)
        print(f"✓ Markdown (with detections): {markdown_det_path}")
    except Exception as e:
        print(f"✗ Failed to download markdown_det: {e}")

    # Download PDF with layouts
    try:
        response = requests.get(f"{server_url}/download/{task_id}/pdf_layout")
        response.raise_for_status()
        pdf_path_out = output_path / f"{Path(pdf_path).stem}_layouts.pdf"
        with open(pdf_path_out, 'wb') as f:
            f.write(response.content)
        results['pdf_layout'] = str(pdf_path_out)
        print(f"✓ PDF (with layouts): {pdf_path_out}")
    except Exception as e:
        print(f"✗ Failed to download PDF layout: {e}")

    # Download images
    try:
        response = requests.get(f"{server_url}/download/{task_id}/images_zip")
        response.raise_for_status()
        images_zip = output_path / "images.zip"
        with open(images_zip, 'wb') as f:
            f.write(response.content)
        results['images_zip'] = str(images_zip)
        print(f"✓ Images: {images_zip}")
    except Exception as e:
        print(f"✗ Failed to download images: {e}")

    print("\n" + "="*60)
    print("Conversion completed successfully!")
    print("="*60)

    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python api_client.py <pdf_file> [server_url] [output_dir]")
        print("\nExample:")
        print("  python api_client.py document.pdf")
        print("  python api_client.py document.pdf http://localhost:8000")
        print("  python api_client.py document.pdf http://localhost:8000 ./my_output")
        sys.exit(1)

    pdf_file = sys.argv[1]
    server_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "./output"

    if not os.path.exists(pdf_file):
        print(f"Error: PDF file not found: {pdf_file}")
        sys.exit(1)

    results = simple_convert(pdf_file, server_url, output_dir)

    if results:
        print("\nOutput files:")
        for key, path in results.items():
            print(f"  {key}: {path}")
    else:
        print("\nConversion failed!")
        sys.exit(1)
