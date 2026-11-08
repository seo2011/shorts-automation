from typing import List, Optional
from .config import settings
from .models import ScriptScene, ImageGenerationResult
from pathlib import Path
import requests
import base64
import time
import zlib
import urllib.parse
from tqdm import tqdm


class ImageGenerator:
    def __init__(self):
        self.api_url = settings.sdxl_api_url
        self.replicate_token = settings.replicate_api_token
        self.output_dir = Path(settings.output_dir) / "images"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_for_scene(
        self, scene: ScriptScene, video_id: str
    ) -> ImageGenerationResult:
        enhanced_prompt = self._enhance_prompt(scene.image_prompt)

        if self.replicate_token:
            return self._generate_replicate(
                enhanced_prompt, scene.scene_number, video_id
            )
        elif self.api_url:
            return self._generate_local_api(
                enhanced_prompt, scene.scene_number, video_id
            )
        else:
            return self._generate_pollinations(
                enhanced_prompt, scene.scene_number, video_id
            )

    def _enhance_prompt(self, prompt: str) -> str:
        style_suffix = (
            "vertical 9:16 aspect ratio, cinematic lighting, 8k resolution, "
            "highly detailed, photorealistic, dramatic atmosphere, "
            "documentary style, sharp focus, professional photography"
        )
        return f"{prompt}, {style_suffix}"

    def _generate_replicate(
        self, prompt: str, scene_num: int, video_id: str
    ) -> ImageGenerationResult:
        headers = {
            "Authorization": f"Token {self.replicate_token}",
            "Content-Type": "application/json",
        }
        data = {
            "version": "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
            "input": {
                "prompt": prompt,
                "negative_prompt": "horizontal, landscape, low quality, blur, watermark, text",
                "aspect_ratio": "9:16",
                "output_format": "png",
                "num_inference_steps": 25,
                "guidance_scale": 7.5,
            },
        }

        response = requests.post(
            "https://api.replicate.com/v1/predictions", headers=headers, json=data
        )
        response.raise_for_status()
        prediction = response.json()
        get_url = prediction["urls"]["get"]

        for _ in range(60):
            time.sleep(5)
            r = requests.get(get_url, headers=headers)
            r.raise_for_status()
            status = r.json()["status"]
            if status == "succeeded":
                image_url = r.json()["output"][0]
                break
            elif status == "failed":
                raise Exception(f"Replicate generation failed: {r.json().get('error')}")
        else:
            raise TimeoutError("Image generation timeout")

        local_path = self._download_image(image_url, video_id, scene_num)
        return ImageGenerationResult(
            scene_number=scene_num,
            image_url=image_url,
            local_path=local_path,
            prompt_used=prompt,
        )

    def _generate_local_api(
        self, prompt: str, scene_num: int, video_id: str
    ) -> ImageGenerationResult:
        data = {
            "prompt": prompt,
            "negative_prompt": "horizontal, landscape, low quality, blur, watermark, text",
            "steps": 25,
            "cfg_scale": 7.5,
            "width": 576,
            "height": 1024,
            "sampler_name": "DPM++ 2M Karras",
            "batch_size": 1,
        }
        response = requests.post(
            f"{self.api_url}/sdapi/v1/txt2img", json=data, timeout=300
        )
        response.raise_for_status()
        result = response.json()

        img_data = base64.b64decode(result["images"][0])
        local_path = self.output_dir / f"{video_id}_scene{scene_num:02d}.png"
        local_path.write_bytes(img_data)

        return ImageGenerationResult(
            scene_number=scene_num,
            image_url="",
            local_path=str(local_path),
            prompt_used=prompt,
        )

    def _generate_pollinations(
        self, prompt: str, scene_num: int, video_id: str
    ) -> ImageGenerationResult:
        """무료 이미지 생성 (Pollinations.ai, API 키 불필요)."""
        seed = zlib.crc32(f"{video_id}-{scene_num}".encode()) % 1_000_000
        encoded = urllib.parse.quote(prompt[:900], safe="")
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width=1080&height=1920&model=flux&nologo=true&seed={seed}"
        )

        last_error = None
        for attempt in range(3):
            try:
                response = requests.get(url, timeout=180)
                response.raise_for_status()
                content_type = response.headers.get("Content-Type", "")
                if (
                    not content_type.startswith("image")
                    or len(response.content) < 20000
                ):
                    raise ValueError(f"invalid image response ({content_type})")
                local_path = self.output_dir / f"{video_id}_scene{scene_num:02d}.jpg"
                local_path.write_bytes(response.content)
                return ImageGenerationResult(
                    scene_number=scene_num,
                    image_url=url,
                    local_path=str(local_path),
                    prompt_used=prompt,
                )
            except Exception as e:
                last_error = e
                print(f"  Pollinations 시도 {attempt + 1}/3 실패: {e}")
                time.sleep(4)

        raise RuntimeError(f"Pollinations 이미지 생성 실패: {last_error}")

    def _generate_placeholder(
        self, scene_num: int, video_id: str
    ) -> ImageGenerationResult:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (576, 1024), color=(30, 30, 40))
        draw = ImageDraw.Draw(img)
        draw.text((50, 500), f"Scene {scene_num}\n{video_id[:8]}", fill=(200, 200, 200))
        local_path = (
            self.output_dir / f"{video_id}_scene{scene_num:02d}_placeholder.png"
        )
        img.save(local_path)
        return ImageGenerationResult(
            scene_number=scene_num,
            image_url="",
            local_path=str(local_path),
            prompt_used="placeholder",
        )

    def _download_image(self, url: str, video_id: str, scene_num: int) -> str:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        local_path = self.output_dir / f"{video_id}_scene{scene_num:02d}.png"
        local_path.write_bytes(response.content)
        return str(local_path)

    def generate_all(
        self, scenes: List[ScriptScene], video_id: str
    ) -> List[ImageGenerationResult]:
        results = []
        for scene in tqdm(scenes, desc="Generating images"):
            try:
                result = self.generate_for_scene(scene, video_id)
                results.append(result)
            except Exception as e:
                print(f"Scene {scene.scene_number} 이미지 생성 실패: {e}")
                results.append(self._generate_placeholder(scene.scene_number, video_id))
        return results


image_generator = ImageGenerator()
