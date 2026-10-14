"""Backup do banco SQLite do ERP.

Roda automaticamente quando o backend sobe (ver `lifespan` em main.py) e
tambem pode ser chamado na mao:

    python backup.py            # respeita o intervalo minimo
    python backup.py --force    # gera um backup agora

Configuracao pelo .env: BACKUP_DIR, BACKUP_EXTERNAL_DIR, BACKUP_RETENTION,
BACKUP_MIN_INTERVAL_HOURS.
"""

import argparse
import os
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv

from database import BASE_DIR, DB_PATH

load_dotenv()

BACKUP_DIR = Path(os.getenv("BACKUP_DIR") or BASE_DIR / "backups")
EXTERNAL_BACKUP_DIR = os.getenv("BACKUP_EXTERNAL_DIR", "").strip()
RETENTION = int(os.getenv("BACKUP_RETENTION", "30"))
MIN_INTERVAL_HOURS = int(os.getenv("BACKUP_MIN_INTERVAL_HOURS", "12"))

FILE_PREFIX = "erp-"
FILE_SUFFIX = ".db"


def _existing_backups() -> list[Path]:
    if not BACKUP_DIR.is_dir():
        return []

    files = BACKUP_DIR.glob(f"{FILE_PREFIX}*{FILE_SUFFIX}")
    return sorted(files, key=lambda path: path.stat().st_mtime)


def _is_backup_due() -> bool:
    backups = _existing_backups()
    if not backups:
        return True

    last_backup = datetime.fromtimestamp(backups[-1].stat().st_mtime)
    return datetime.now() - last_backup >= timedelta(hours=MIN_INTERVAL_HOURS)


def _build_destination(timestamp: str) -> Path:
    destination = BACKUP_DIR / f"{FILE_PREFIX}{timestamp}{FILE_SUFFIX}"

    counter = 2
    while destination.exists():
        destination = BACKUP_DIR / f"{FILE_PREFIX}{timestamp}-{counter}{FILE_SUFFIX}"
        counter += 1

    return destination


def _copy_database(destination: Path) -> None:
    with closing(sqlite3.connect(DB_PATH)) as source:
        with closing(sqlite3.connect(destination)) as target:
            source.backup(target)


def _prune_old_backups() -> int:
    backups = _existing_backups()
    excess = len(backups) - RETENTION
    if excess <= 0:
        return 0

    for old_backup in backups[:excess]:
        old_backup.unlink(missing_ok=True)

    return excess


def _mirror_to_external(backup_path: Path) -> Path | None:
    if not EXTERNAL_BACKUP_DIR:
        return None

    try:
        external_dir = Path(EXTERNAL_BACKUP_DIR)
        external_dir.mkdir(parents=True, exist_ok=True)
        destination = external_dir / backup_path.name
        shutil.copy2(backup_path, destination)
        return destination
    except OSError as error:
        print(f"[backup] copia externa falhou: {error}")
        return None


def create_backup(force: bool = False) -> Path | None:
    """Gera um backup consistente do banco. Devolve None se nao era hora."""
    if not DB_PATH.is_file():
        print("[backup] banco ainda nao existe, nada a copiar")
        return None

    if not force and not _is_backup_due():
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = _build_destination(timestamp)

    _copy_database(destination)
    size_kb = destination.stat().st_size / 1024
    print(f"[backup] gerado {destination} ({size_kb:.0f} KB)")

    removed = _prune_old_backups()
    if removed:
        print(f"[backup] {removed} backup(s) antigo(s) removido(s)")

    mirrored = _mirror_to_external(destination)
    if mirrored:
        print(f"[backup] copia externa em {mirrored}")

    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gera um backup do banco do ERP")
    parser.add_argument(
        "--force",
        action="store_true",
        help="gera o backup mesmo que o intervalo minimo nao tenha passado",
    )
    args = parser.parse_args()

    if create_backup(force=args.force) is None and not args.force:
        print("[backup] backup recente ja existe, use --force para forcar")
