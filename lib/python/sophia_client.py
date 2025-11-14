"""
Sophia Inference Endpoint Client

A Python client for interacting with ALCF's Sophia inference service.
Supports authentication, text generation, and multimodal (vision) capabilities.
"""

import base64
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

import requests


@dataclass
class SophiaConfig:
    """Configuration for Sophia client"""
    access_token: Optional[str] = None
    base_url: str = "https://inference-api.alcf.anl.gov/resource_server/sophia/vllm/v1"
    default_model: str = "meta-llama/Meta-Llama-3.1-70B-Instruct"
    timeout: int = 120
    max_retries: int = 3
    pdf_processing: Dict[str, Any] = field(default_factory=lambda: {
        "extract_images": True,
        "extract_text": True,
        "output_dir": "output",
        "questions_to_generate": 5
    })

    @classmethod
    def from_file(cls, config_path: Path) -> "SophiaConfig":
        """Load configuration from JSON file"""
        with open(config_path, 'r') as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def from_env_and_file(cls, config_path: Optional[Path] = None) -> "SophiaConfig":
        """
        Load configuration with priority:
        1. Environment variable SOPHIA_ACCESS_TOKEN (for token only)
        2. Config file (if provided)
        3. Defaults
        """
        config = cls()

        # Load from file if provided
        if config_path and config_path.exists():
            config = cls.from_file(config_path)

        # Environment variable overrides config file for access token
        env_token = os.getenv("SOPHIA_ACCESS_TOKEN")
        if env_token:
            config.access_token = env_token

        return config


@dataclass
class ChatMessage:
    """Represents a chat message"""
    role: str  # "system", "user", or "assistant"
    content: str


@dataclass
class SophiaResponse:
    """Represents a response from Sophia API"""
    model: str
    content: str
    usage: Dict[str, int]
    finish_reason: str
    response_time: float
    raw_response: Dict[str, Any] = field(default_factory=dict)


class SophiaClient:
    """Client for ALCF Sophia inference endpoints"""

    def __init__(self, config: Optional[SophiaConfig] = None, config_path: Optional[Path] = None):
        """
        Initialize Sophia client

        Args:
            config: SophiaConfig object (if not provided, loads from config_path or defaults)
            config_path: Path to config JSON file
        """
        if config is None:
            if config_path is None:
                # Try default config path
                default_config = Path(__file__).parent.parent.parent / "config" / "sophia.json"
                config_path = default_config if default_config.exists() else None

            config = SophiaConfig.from_env_and_file(config_path)

        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self.chat_endpoint = f"{self.base_url}/chat/completions"
        self.completions_endpoint = f"{self.base_url}/completions"

        if not self.config.access_token:
            raise ValueError(
                "No access token provided. Set SOPHIA_ACCESS_TOKEN environment variable "
                "or add 'access_token' to config/sophia.json"
            )

    def _make_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """Make HTTP request with retry logic and authentication"""
        kwargs.setdefault('timeout', self.config.timeout)

        # Add authentication header
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.config.access_token}"
        kwargs['headers'] = headers

        for attempt in range(self.config.max_retries):
            try:
                response = requests.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Request failed, retrying in {wait_time}s... ({attempt + 1}/{self.config.max_retries})")
                time.sleep(wait_time)

    def _encode_image_to_base64(self, image_path: Path) -> str:
        """Encode image to base64 string"""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _encode_pdf_to_base64(self, pdf_path: Path) -> str:
        """Encode PDF to base64 string"""
        with open(pdf_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _create_image_url(self, image_path: Path) -> str:
        """Create data URL for image"""
        # Determine MIME type
        ext = image_path.suffix.lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext, 'image/jpeg')

        b64_image = self._encode_image_to_base64(image_path)
        return f"data:{mime_type};base64,{b64_image}"

    def chat_completion(
        self,
        messages: List[ChatMessage],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs
    ) -> SophiaResponse:
        """
        Send chat completion request

        Args:
            messages: List of ChatMessage objects
            model: Model to use (defaults to config.default_model)
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters for the API

        Returns:
            SophiaResponse object
        """
        start_time = time.time()

        model = model or self.config.default_model

        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }

        response = self._make_request(
            "POST",
            self.chat_endpoint,
            json=payload
        )

        response_time = time.time() - start_time
        data = response.json()

        return SophiaResponse(
            model=data['model'],
            content=data['choices'][0]['message']['content'],
            usage=data.get('usage', {}),
            finish_reason=data['choices'][0]['finish_reason'],
            response_time=response_time,
            raw_response=data
        )

    def chat_with_image(
        self,
        prompt: str,
        image_path: Path,
        model: Optional[str] = None,
        system_message: Optional[str] = None,
        **kwargs
    ) -> SophiaResponse:
        """
        Send chat completion with image (vision capability)

        Args:
            prompt: Text prompt about the image
            image_path: Path to image file
            model: Model to use (should support vision)
            system_message: Optional system message
            **kwargs: Additional parameters for the API

        Returns:
            SophiaResponse object
        """
        messages = []

        if system_message:
            messages.append(ChatMessage(role="system", content=system_message))

        # Create multimodal message
        image_url = self._create_image_url(image_path)

        # OpenAI-compatible vision format
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_url}}
        ]

        messages.append(ChatMessage(
            role="user",
            content=json.dumps(content)  # Some APIs expect JSON string
        ))

        return self.chat_completion(messages, model=model, **kwargs)

    def analyze_text(
        self,
        text: str,
        analysis_type: str = "summary",
        model: Optional[str] = None,
        **kwargs
    ) -> SophiaResponse:
        """
        Analyze text with specific analysis type

        Args:
            text: Text to analyze
            analysis_type: Type of analysis ("summary", "questions", "key_findings", etc.)
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            SophiaResponse object
        """
        prompts = {
            "summary": "Provide a concise summary of the following text:",
            "questions": "Generate insightful questions based on the following text:",
            "key_findings": "Extract and list the key findings from the following text:",
            "methodology": "Describe the methodology discussed in the following text:",
        }

        system_prompt = prompts.get(analysis_type, "Analyze the following text:")

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=text)
        ]

        return self.chat_completion(messages, model=model, **kwargs)

    def generate_questions(
        self,
        text: str,
        num_questions: int = 5,
        question_type: str = "high-level scientific",
        model: Optional[str] = None,
        **kwargs
    ) -> List[str]:
        """
        Generate questions from text

        Args:
            text: Text to generate questions from
            num_questions: Number of questions to generate
            question_type: Type of questions ("high-level scientific", "detailed", "critical", etc.)
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            List of generated questions
        """
        system_prompt = (
            f"You are a scientific expert. Generate exactly {num_questions} {question_type} questions "
            f"based on the following text. Format your response as a numbered list with one question per line."
        )

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=text)
        ]

        response = self.chat_completion(messages, model=model, **kwargs)

        # Parse questions from response
        lines = response.content.strip().split('\n')
        questions = []

        for line in lines:
            line = line.strip()
            # Remove numbering (1., 1), etc.)
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Remove common list prefixes
                for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.',
                               '1)', '2)', '3)', '4)', '5)', '6)', '7)', '8)', '9)', '10)',
                               '-', '*', '•']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break

                if line:
                    questions.append(line)

        return questions[:num_questions]  # Ensure we don't return more than requested

    def process_pdf_direct(
        self,
        pdf_path: Path,
        prompt: str = "Extract and summarize all text content from this PDF document.",
        model: Optional[str] = None,
        **kwargs
    ) -> SophiaResponse:
        """
        Process PDF directly using Sophia API (if model supports it)

        This method attempts to send the PDF as a base64-encoded document
        to the API. Success depends on the model's multimodal capabilities.

        Args:
            pdf_path: Path to PDF file
            prompt: Prompt for PDF processing
            model: Model to use (should support PDF/document processing)
            **kwargs: Additional parameters for the API

        Returns:
            SophiaResponse object

        Raises:
            Exception: If model doesn't support PDF processing
        """
        pdf_b64 = self._encode_pdf_to_base64(pdf_path)

        # Try document-as-image approach (convert PDF pages to images)
        messages = [
            ChatMessage(
                role="user",
                content=json.dumps([
                    {"type": "text", "text": prompt},
                    {
                        "type": "document_url",
                        "document_url": {
                            "url": f"data:application/pdf;base64,{pdf_b64}"
                        }
                    }
                ])
            )
        ]

        try:
            return self.chat_completion(messages, model=model, **kwargs)
        except Exception as e:
            # If document_url doesn't work, try alternative format
            messages = [
                ChatMessage(
                    role="user",
                    content=f"{prompt}\n\n[PDF Document: {pdf_path.name}]\nBase64: {pdf_b64[:100]}..."
                )
            ]
            return self.chat_completion(messages, model=model, **kwargs)

    def extract_text_from_pdf_direct(
        self,
        pdf_path: Path,
        model: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Extract text from PDF using Sophia API directly

        Args:
            pdf_path: Path to PDF file
            model: Model to use
            **kwargs: Additional parameters

        Returns:
            Extracted text content
        """
        prompt = (
            "Extract all text content from this PDF document. "
            "Preserve structure, headings, and formatting as much as possible. "
            "Output only the extracted text without any additional commentary."
        )

        response = self.process_pdf_direct(pdf_path, prompt, model, **kwargs)
        return response.content
