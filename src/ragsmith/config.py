"""Configuration for RagSmith."""
from dataclasses import dataclass
from typing import Optional


def _env_bool(name: str, default: bool) -> bool:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class RagSmithConfig:
    backend: str = "docling"
    reflow: bool = True
    split_sections: bool = False
    overwrite: bool = False

    @classmethod
    def from_env(cls) -> "RagSmithConfig":
        import os

        return cls(
            backend=os.getenv("RAGSMITH_BACKEND", cls.backend),
            reflow=_env_bool("RAGSMITH_REFLOW", cls.reflow),
            split_sections=_env_bool("RAGSMITH_SPLIT_SECTIONS", cls.split_sections),
            overwrite=_env_bool("RAGSMITH_OVERWRITE", cls.overwrite),
        )

    def with_overrides(
        self,
        *,
        backend: Optional[str] = None,
        reflow: Optional[bool] = None,
        split_sections: Optional[bool] = None,
        overwrite: Optional[bool] = None,
    ) -> "RagSmithConfig":
        return RagSmithConfig(
            backend=backend if backend is not None else self.backend,
            reflow=self.reflow if reflow is None else reflow,
            split_sections=self.split_sections if split_sections is None else split_sections,
            overwrite=self.overwrite if overwrite is None else overwrite,
        )


__all__ = ["RagSmithConfig"]
