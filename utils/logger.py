import logging
import sys
from pathlib import Path


def kur(seviye: str = "INFO", dosya: str | None = "goruntu_isleme.log") -> None:
    fmt = "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if dosya:
        Path(dosya).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(dosya, encoding="utf-8"))

    logging.basicConfig(
        level=getattr(logging, seviye.upper(), logging.INFO),
        format=fmt,
        handlers=handlers,
    )
    # Ultralytics'in aşırı verbose çıktısını kapat
    logging.getLogger("ultralytics").setLevel(logging.WARNING)
