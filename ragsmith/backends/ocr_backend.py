"""OCR backend implementation using EasyOCR and PyMuPDF."""
from __future__ import annotations

import logging
import re
import tempfile
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Iterable, List, Literal, Sequence

from ragsmith.backends.base import PdfToMarkdownBackend
from ragsmith.errors import BackendConversionError, BackendNotAvailableError

LOGGER = logging.getLogger("ragsmith.backends.ocr")


_WHITESPACE_RE = re.compile(r" {2,}")
_MULTIPLE_BLANK_LINES_RE = re.compile(r"\n{3,}")
_HYPHEN_SPLIT_RE = re.compile(r"(\w+)-\n(\w+)")
_PAGE_NUMBER_LINE_RE_1 = re.compile(r"\d{1,4}$")
_PAGE_NUMBER_LINE_RE_2 = re.compile(r"-?\d{1,4}-?$")
_LIST_ITEM_RE = re.compile(r"^\d+[\.\)] ")


def _clean_page_text(raw_text: str) -> str:
    text = raw_text

    while True:
        new_text = _HYPHEN_SPLIT_RE.sub(r"\1\2", text)
        if new_text == text:
            break
        text = new_text

    cleaned_lines: List[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            cleaned_lines.append(line)
            continue

        if _PAGE_NUMBER_LINE_RE_1.fullmatch(stripped):
            continue
        if _PAGE_NUMBER_LINE_RE_2.fullmatch(stripped):
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines).strip()

    text = text.replace("\t", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _MULTIPLE_BLANK_LINES_RE.sub("\n\n", text)
    lines = [_WHITESPACE_RE.sub(" ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines).strip()

    lines = text.split("\n")
    out_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            out_lines.append(line)
            continue
        if stripped.startswith("- ") or _LIST_ITEM_RE.match(stripped):
            out_lines.append(line)
            continue

        letters = [c for c in stripped if c.isalpha()]
        upper_letters = [c for c in letters if c.isupper()]
        caps_ratio = (len(upper_letters) / len(letters)) if letters else 0.0

        if len(stripped) <= 60 and caps_ratio >= 0.8:
            out_lines.append(f"### {stripped.title()}")
        else:
            out_lines.append(line)

    return "\n".join(out_lines).strip()


class OCRBackend(PdfToMarkdownBackend):
    """Backend that rasterizes PDF pages then extracts text via EasyOCR."""

    def __init__(
        self,
        *,
        languages: Sequence[str] | None = None,
        device: Literal["auto", "cpu", "cuda", "mps"] = "auto",
        dpi: int = 300,
        start_page: int | None = None,
        end_page: int | None = None,
    ) -> None:
        self.languages = list(languages or ["en"])
        self.device_preference = device
        self.dpi = dpi
        self.start_page = start_page
        self.end_page = end_page

        self._torch = None
        self._fitz = None
        self._easyocr = None
        self._tqdm = None

        self._load_dependencies()
        self.device = self._select_device()
        self._reader = self._init_reader()

    def _load_dependencies(self) -> None:
        missing: list[str] = []
        for module_name in ("easyocr", "torch", "fitz", "tqdm"):
            if find_spec(module_name) is None:
                missing.append(module_name)
        if missing:
            raise BackendNotAvailableError(
                f"OCR dependencies missing; install {', '.join(missing)}",
            )

        self._easyocr = import_module("easyocr")
        self._torch = import_module("torch")
        self._fitz = import_module("fitz")
        self._tqdm = import_module("tqdm")

    def _select_device(self) -> str:
        torch_module = self._torch
        if self.device_preference == "mps":
            if getattr(torch_module.backends, "mps", None) and torch_module.backends.mps.is_available():
                return "mps"
            LOGGER.warning("MPS requested but unavailable; falling back to CPU")
            return "cpu"

        if self.device_preference == "cuda":
            if torch_module.cuda.is_available():
                return "cuda"
            LOGGER.warning("CUDA requested but unavailable; falling back to CPU")
            return "cpu"

        if self.device_preference == "auto":
            if torch_module.cuda.is_available():
                return "cuda"
            if getattr(torch_module.backends, "mps", None) and torch_module.backends.mps.is_available():
                return "mps"
            return "cpu"

        return "cpu"

    def _init_reader(self):
        use_gpu = self.device != "cpu"
        LOGGER.info(
            "Initializing EasyOCR with languages=%s on device=%s (gpu flag: %s)",
            self.languages,
            self.device,
            use_gpu,
        )
        return self._easyocr.Reader(self.languages, gpu=use_gpu)

    def _page_range(self, total_pages: int) -> Iterable[int]:
        start_page = self.start_page or 1
        end_page = self.end_page or total_pages
        if start_page < 1:
            start_page = 1
        if end_page < start_page:
            end_page = start_page
        if end_page > total_pages:
            end_page = total_pages
        return range(start_page - 1, end_page)

    def convert(self, pdf_path: Path) -> str:
        LOGGER.info(
            "Converting %s with OCR (dpi=%s, languages=%s, device=%s)",
            pdf_path,
            self.dpi,
            self.languages,
            self.device,
        )
        try:
            document = self._fitz.open(pdf_path)
        except Exception as exc:  # pragma: no cover - PyMuPDF internals
            raise BackendConversionError(f"Failed to open {pdf_path}: {exc}") from exc

        combined_parts: List[str] = []
        page_indices = list(self._page_range(len(document)))

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            for page_index in self._tqdm.tqdm(page_indices, desc="OCR", unit="page"):
                page_number = page_index + 1
                try:
                    page = document[page_index]
                    zoom = self.dpi / 72.0
                    pixmap = page.get_pixmap(matrix=self._fitz.Matrix(zoom, zoom), alpha=False)
                    image_path = tmpdir_path / f"page_{page_number:04d}.png"
                    pixmap.save(image_path)

                    text_blocks = self._reader.readtext(str(image_path), detail=0, paragraph=True)
                    raw_text = "\n\n".join(text_blocks).strip()
                    cleaned_text = _clean_page_text(raw_text)
                    combined_parts.append(f"## Page {page_number}\n\n{cleaned_text}\n")
                except Exception as exc:  # pragma: no cover - per-page failures vary
                    LOGGER.error("Failed to process page %s of %s: %s", page_number, pdf_path, exc)
                    continue

        if not combined_parts:
            raise BackendConversionError(f"OCR produced no text for {pdf_path}")

        return "\n\n---\n\n".join(combined_parts)


__all__ = ["OCRBackend"]
