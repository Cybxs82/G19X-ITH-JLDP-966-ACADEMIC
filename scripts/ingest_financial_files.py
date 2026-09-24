"""Batch loader for ERP and bank financial files."""

import argparse
from pathlib import Path

from backend.services.ingestion_service import ingest_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Extrae, normaliza y carga archivos financieros a PostgreSQL")
    parser.add_argument("files", nargs="+", type=Path, help="Archivos .xlsx, .csv o .pdf")
    parser.add_argument("--source-type", choices=("erp", "banco"), default="erp")
    args = parser.parse_args()

    for path in args.files:
        result = ingest_file(path.name, path.read_bytes(), args.source_type)
        print(
            "%s: %s filas cargadas (sync_log_id=%s)"
            % (path, result["rows_ingested"], result["sync_log_id"])
        )


if __name__ == "__main__":
    main()
