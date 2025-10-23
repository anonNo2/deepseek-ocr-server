import os
import re
import io
import fitz
import img2pdf
import torch
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vllm import LLM, SamplingParams
from vllm.model_executor.models.registry import ModelRegistry

from deepseek_ocr import DeepseekOCRForCausalLM
from process.ngram_norepeat import NoRepeatNGramLogitsProcessor
from process.image_process import DeepseekOCRProcessor

from config import ModelConfig


class PDFProcessor:
    """PDF to Markdown Processor using DeepSeek OCR"""

    def __init__(self):
        """Initialize the PDF processor with model"""
        self.setup_environment()
        self.load_model()
        self.processor = DeepseekOCRProcessor()

    def setup_environment(self):
        """Setup environment variables"""
        if torch.version.cuda == '11.8':
            os.environ["TRITON_PTXAS_PATH"] = "/usr/local/cuda-11.8/bin/ptxas"
        os.environ['VLLM_USE_V1'] = '0'

        if ModelConfig.CUDA_VISIBLE_DEVICES:
            os.environ["CUDA_VISIBLE_DEVICES"] = ModelConfig.CUDA_VISIBLE_DEVICES

    def load_model(self):
        """Load the DeepSeek OCR model"""
        print(f"Loading model from {ModelConfig.MODEL_PATH}")

        # Register model
        ModelRegistry.register_model("DeepseekOCRForCausalLM", DeepseekOCRForCausalLM)

        # Initialize LLM
        self.llm = LLM(
            model=ModelConfig.MODEL_PATH,
            hf_overrides={"architectures": ["DeepseekOCRForCausalLM"]},
            block_size=256,
            enforce_eager=False,
            trust_remote_code=True,
            max_model_len=8192,
            swap_space=0,
            max_num_seqs=ModelConfig.MAX_CONCURRENCY,
            tensor_parallel_size=1,
            gpu_memory_utilization=ModelConfig.GPU_MEMORY_UTILIZATION,
            disable_mm_preprocessor_cache=True
        )

        # Setup logits processors
        self.logits_processors = [
            NoRepeatNGramLogitsProcessor(
                ngram_size=20,
                window_size=50,
                whitelist_token_ids={128821, 128822}  # <td>,</td>
            )
        ]

        # Setup sampling params
        self.sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=8192,
            logits_processors=self.logits_processors,
            skip_special_tokens=False,
            include_stop_str_in_output=True,
        )

        print("Model loaded successfully")

    def pdf_to_images(self, pdf_path: str, dpi: int = 144) -> list:
        """Convert PDF pages to images"""
        images = []
        pdf_document = fitz.open(pdf_path)

        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_num in range(pdf_document.page_count):
            page = pdf_document[page_num]
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            Image.MAX_IMAGE_PIXELS = None

            img_data = pixmap.tobytes("png")
            img = Image.open(io.BytesIO(img_data))

            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            images.append(img)

        pdf_document.close()
        return images

    def images_to_pdf(self, pil_images: list, output_path: str):
        """Convert PIL images to PDF"""
        if not pil_images:
            return

        image_bytes_list = []

        for img in pil_images:
            if img.mode != 'RGB':
                img = img.convert('RGB')

            img_buffer = io.BytesIO()
            img.save(img_buffer, format='JPEG', quality=95)
            img_bytes = img_buffer.getvalue()
            image_bytes_list.append(img_bytes)

        try:
            pdf_bytes = img2pdf.convert(image_bytes_list)
            with open(output_path, "wb") as f:
                f.write(pdf_bytes)
        except Exception as e:
            print(f"Error converting images to PDF: {e}")

    def extract_references(self, text: str):
        """Extract reference tags from text"""
        pattern = r'(<\|ref\|>(.*?)<\|/ref\|><\|det\|>(.*?)<\|/det\|>)'
        matches = re.findall(pattern, text, re.DOTALL)

        matches_image = []
        matches_other = []
        for a_match in matches:
            if '<|ref|>image<|/ref|>' in a_match[0]:
                matches_image.append(a_match[0])
            else:
                matches_other.append(a_match[0])

        return matches, matches_image, matches_other

    def extract_coordinates_and_label(self, ref_text, image_width, image_height):
        """Extract coordinates and label from reference text"""
        try:
            label_type = ref_text[1]
            cor_list = eval(ref_text[2])
        except Exception as e:
            print(f"Error extracting coordinates: {e}")
            return None

        return (label_type, cor_list)

    def draw_bounding_boxes(self, image, refs, page_idx, images_dir):
        """Draw bounding boxes on image"""
        image_width, image_height = image.size
        img_draw = image.copy()
        draw = ImageDraw.Draw(img_draw)

        overlay = Image.new('RGBA', img_draw.size, (0, 0, 0, 0))
        draw2 = ImageDraw.Draw(overlay)

        font = ImageFont.load_default()

        img_idx = 0

        for i, ref in enumerate(refs):
            try:
                result = self.extract_coordinates_and_label(ref, image_width, image_height)
                if result:
                    label_type, points_list = result

                    color = (np.random.randint(0, 200), np.random.randint(0, 200), np.random.randint(0, 255))
                    color_a = color + (20,)

                    for points in points_list:
                        x1, y1, x2, y2 = points

                        x1 = int(x1 / 999 * image_width)
                        y1 = int(y1 / 999 * image_height)
                        x2 = int(x2 / 999 * image_width)
                        y2 = int(y2 / 999 * image_height)

                        if label_type == 'image':
                            try:
                                cropped = image.crop((x1, y1, x2, y2))
                                cropped.save(f"{images_dir}/{page_idx}_{img_idx}.jpg")
                            except Exception as e:
                                print(f"Error saving cropped image: {e}")
                                pass
                            img_idx += 1

                        try:
                            if label_type == 'title':
                                draw.rectangle([x1, y1, x2, y2], outline=color, width=4)
                                draw2.rectangle([x1, y1, x2, y2], fill=color_a, outline=(0, 0, 0, 0), width=1)
                            else:
                                draw.rectangle([x1, y1, x2, y2], outline=color, width=2)
                                draw2.rectangle([x1, y1, x2, y2], fill=color_a, outline=(0, 0, 0, 0), width=1)

                            text_x = x1
                            text_y = max(0, y1 - 15)

                            text_bbox = draw.textbbox((0, 0), label_type, font=font)
                            text_width = text_bbox[2] - text_bbox[0]
                            text_height = text_bbox[3] - text_bbox[1]
                            draw.rectangle([text_x, text_y, text_x + text_width, text_y + text_height],
                                         fill=(255, 255, 255, 30))

                            draw.text((text_x, text_y), label_type, font=font, fill=color)
                        except:
                            pass
            except:
                continue

        img_draw.paste(overlay, (0, 0), overlay)
        return img_draw

    def process_single_image(self, image, prompt: str, crop_mode: bool):
        """Process a single image"""
        cache_item = {
            "prompt": prompt,
            "multi_modal_data": {
                "image": self.processor.tokenize_with_images(
                    images=[image],
                    bos=True,
                    eos=True,
                    cropping=crop_mode
                )
            },
        }
        return cache_item

    def process_pdf(
        self,
        input_path: str,
        output_dir: str,
        prompt: str = None,
        skip_repeat: bool = True,
        crop_mode: bool = True
    ) -> dict:
        """
        Process PDF and convert to Markdown

        Args:
            input_path: Path to input PDF file
            output_dir: Output directory for results
            prompt: Custom prompt (optional)
            skip_repeat: Skip pages without EOS token
            crop_mode: Enable crop mode

        Returns:
            dict with paths to output files
        """

        # Setup directories
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        images_dir = output_path / 'images'
        images_dir.mkdir(exist_ok=True)

        # Use default prompt if not provided
        if prompt is None:
            prompt = ModelConfig.DEFAULT_PROMPT

        print(f"Loading PDF: {input_path}")
        images = self.pdf_to_images(input_path)
        print(f"Loaded {len(images)} pages")

        # Process images in parallel
        print("Preprocessing images...")
        with ThreadPoolExecutor(max_workers=ModelConfig.NUM_WORKERS) as executor:
            batch_inputs = list(tqdm(
                executor.map(
                    lambda img: self.process_single_image(img, prompt, crop_mode),
                    images
                ),
                total=len(images),
                desc="Preprocessing"
            ))

        # Generate OCR outputs
        print("Running OCR inference...")
        outputs_list = self.llm.generate(
            batch_inputs,
            sampling_params=self.sampling_params
        )

        # Process outputs
        print("Processing outputs...")
        pdf_name = Path(input_path).stem

        mmd_det_path = output_path / f'{pdf_name}_det.mmd'
        mmd_path = output_path / f'{pdf_name}.mmd'
        pdf_out_path = output_path / f'{pdf_name}_layouts.pdf'

        contents_det = ''
        contents = ''
        draw_images = []

        for page_idx, (output, img) in enumerate(zip(outputs_list, images)):
            content = output.outputs[0].text

            # Check for EOS token
            if '<｜end▁of▁sentence｜>' in content:
                content = content.replace('<｜end▁of▁sentence｜>', '')
            else:
                if skip_repeat:
                    continue

            page_separator = f'\n<--- Page Split --->'

            contents_det += content + f'\n{page_separator}\n'

            # Process references and draw bounding boxes
            matches_ref, matches_images, matches_other = self.extract_references(content)
            result_image = self.draw_bounding_boxes(img, matches_ref, page_idx, images_dir)
            draw_images.append(result_image)

            # Replace image references
            for idx, a_match_image in enumerate(matches_images):
                content = content.replace(
                    a_match_image,
                    f'![](images/{page_idx}_{idx}.jpg)\n'
                )

            # Remove other references
            for idx, a_match_other in enumerate(matches_other):
                content = content.replace(a_match_other, '') \
                    .replace('\\coloneqq', ':=') \
                    .replace('\\eqqcolon', '=:') \
                    .replace('\n\n\n\n', '\n\n') \
                    .replace('\n\n\n', '\n\n')

            contents += content + f'\n{page_separator}\n'

        # Save outputs
        with open(mmd_det_path, 'w', encoding='utf-8') as f:
            f.write(contents_det)

        with open(mmd_path, 'w', encoding='utf-8') as f:
            f.write(contents)

        self.images_to_pdf(draw_images, str(pdf_out_path))

        print(f"Conversion completed!")
        print(f"Markdown: {mmd_path}")
        print(f"Markdown with detections: {mmd_det_path}")
        print(f"PDF with layouts: {pdf_out_path}")

        return {
            "markdown_file": str(mmd_path),
            "markdown_det_file": str(mmd_det_path),
            "pdf_layout_file": str(pdf_out_path),
            "images_dir": str(images_dir)
        }

    def cleanup(self):
        """Cleanup resources"""
        print("Cleaning up resources...")
        # Model cleanup if needed
