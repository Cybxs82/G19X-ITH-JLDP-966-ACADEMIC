"""Ingestion pipeline for ERP and bank files.

The pipeline keeps the original payload in staging, normalizes rows into the
financial model, and materializes dashboard KPIs from the normalized data.
"""

import csv
import io
import json
import re
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..infrastructure.database import get_db_connection


FIELD_ALIASES = {
    "transaction_date": ("transaction_date", "date", "fecha", "fecha_transaccion", "fecha movimiento"),
    "amount": ("amount", "monto", "importe", "valor", "amount_mxn"),
    "account_code": ("account_code", "cuenta", "codigo_cuenta", "account"),
    "account_name": ("account_name", "nombre_cuenta", "cuenta_nombre"),
    "category": ("category", "categoria", "tipo", "clasificacion"),
    "cost_center_code": ("cost_center_code", "centro_costo", "centro de costo", "cost_center"),
    "cost_center_name": ("cost_center_name", "nombre_centro", "centro_nombre"),
    "description": ("description", "descripcion", "concepto", "detalle"),
    "source_reference": ("source_reference", "referencia", "id_transaccion", "folio", "documento"),
    "currency": ("currency", "moneda", "divisa"),
}


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").strip().lower())


def _decimal(value: Any) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    text = str(value).strip().replace("$", "").replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(",", "") if text.rfind(".") > text.rfind(",") else text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError("Monto invalido: %s" % value) from error


def _date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("Fecha invalida: %s" % value)


def _canonical_row(row: Dict[str, Any], position: int) -> Dict[str, Any]:
    normalized = {_key(key): value for key, value in row.items()}
    result: Dict[str, Any] = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if _key(alias) in normalized and normalized[_key(alias)] not in (None, ""):
                result[field] = normalized[_key(alias)]
                break
    if "transaction_date" not in result or "amount" not in result:
        raise ValueError("La fila %s requiere fecha y monto" % position)
    result["transaction_date"] = _date(result["transaction_date"])
    result["amount"] = _decimal(result["amount"])
    result["account_code"] = str(result.get("account_code") or "GENERIC").strip()
    result["account_name"] = str(result.get("account_name") or result["account_code"]).strip()
    result["category"] = str(result.get("category") or "otros").strip().lower()
    result["cost_center_code"] = str(result.get("cost_center_code") or "GENERAL").strip()
    result["cost_center_name"] = str(result.get("cost_center_name") or result["cost_center_code"]).strip()
    result["description"] = str(result.get("description") or "Importado desde archivo").strip()
    result["source_reference"] = str(result.get("source_reference") or "fila-%s" % position).strip()
    result["currency"] = str(result.get("currency") or "MXN").strip().upper()[:3]
    return result


def extract_excel(content: bytes) -> List[Dict[str, Any]]:
    from openpyxl import load_workbook

    workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.active
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(value or "") for value in rows[0]]
    return [dict(zip(headers, values)) for values in rows[1:] if any(value not in (None, "") for value in values)]


def extract_csv(content: bytes) -> List[Dict[str, Any]]:
    text = content.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def extract_pdf(content: bytes) -> List[Dict[str, Any]]:
    from pypdf import PdfReader

    text = "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    rows: List[Dict[str, Any]] = []
    pattern = re.compile(r"(?P<date>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}).*?(?P<amount>-?\$?\d[\d.,]*)")
    for line in text.splitlines():
        match = pattern.search(line)
        if match:
            rows.append({
                "fecha": match.group("date"),
                "monto": match.group("amount"),
                "descripcion": line[: match.start("amount")].strip(),
                "referencia": "pdf-%s" % len(rows),
            })
    if not rows:
        raise ValueError("No se encontraron filas financieras legibles en el PDF")
    return rows


def extract_rows(file_name: str, content: bytes) -> List[Dict[str, Any]]:
    suffix = Path(file_name).suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        raw_rows = extract_excel(content)
    elif suffix == ".csv":
        raw_rows = extract_csv(content)
    elif suffix == ".pdf":
        raw_rows = extract_pdf(content)
    else:
        raise ValueError("Formato no soportado: %s" % suffix)
    return [_canonical_row(row, index) for index, row in enumerate(raw_rows, start=2)]


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _source_id(cursor: Any, source_type: str, file_name: str) -> int:
    cursor.execute(
        """
        INSERT INTO data_sources (name, type, connection_config, is_active)
        VALUES (%s, %s::fuente_tipo, %s::jsonb, TRUE)
        RETURNING id
        """,
        (file_name, source_type, json.dumps({"mode": "file", "file_name": file_name})),
    )
    return cursor.fetchone()[0]


def _upsert_transaction(cursor: Any, row: Dict[str, Any], source_type: str) -> None:
    cursor.execute(
        """
        INSERT INTO accounts (code, name, category)
        VALUES (%s, %s, %s)
        ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, category = EXCLUDED.category
        RETURNING id
        """,
        (row["account_code"], row["account_name"], row["category"]),
    )
    account_id = cursor.fetchone()[0]
    cursor.execute(
        """
        INSERT INTO cost_centers (code, name)
        VALUES (%s, %s)
        ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name
        RETURNING id
        """,
        (row["cost_center_code"], row["cost_center_name"]),
    )
    cost_center_id = cursor.fetchone()[0]
    cursor.execute(
        """
        INSERT INTO transactions
            (account_id, cost_center_id, source_type, source_reference, amount, currency, transaction_date, description)
        VALUES (%s, %s, %s::fuente_tipo, %s, %s, %s, %s, %s)
        ON CONFLICT (source_type, source_reference) DO UPDATE SET
            account_id = EXCLUDED.account_id,
            cost_center_id = EXCLUDED.cost_center_id,
            amount = EXCLUDED.amount,
            currency = EXCLUDED.currency,
            transaction_date = EXCLUDED.transaction_date,
            description = EXCLUDED.description
        """,
        (account_id, cost_center_id, source_type, row["source_reference"], row["amount"], row["currency"], row["transaction_date"], row["description"]),
    )


def _refresh_kpis(cursor: Any) -> None:
    cursor.execute(
        """
        SELECT COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0),
               COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END), 0),
               COALESCE(SUM(t.amount), 0)
        FROM transactions t
        """
    )
    income, expenses, net = [Decimal(str(value)) for value in cursor.fetchone()]
    liquidity = income / expenses if expenses else Decimal("0")
    margin = net / income * Decimal("100") if income else Decimal("0")
    cursor.execute("SELECT COALESCE(SUM(b.budgeted_amount), 0) FROM budgets b")
    budget = Decimal(str(cursor.fetchone()[0]))
    deviation = ((expenses - budget) / budget * Decimal("100")) if budget else Decimal("0")
    values = [(1, liquidity), (2, margin), (3, income), (4, deviation)]
    period = date.today().replace(day=1)
    cursor.execute(
        "DELETE FROM kpi_values WHERE kpi_id IN (1, 2, 3, 4) AND cost_center_id IS NULL AND period = %s",
        (period,),
    )
    for kpi_id, value in values:
        cursor.execute(
            """
            INSERT INTO kpi_values (kpi_id, cost_center_id, period, value, calculated_at)
            VALUES (%s, NULL, %s, %s, %s)
            ON CONFLICT (kpi_id, cost_center_id, period) DO UPDATE SET value = EXCLUDED.value, calculated_at = EXCLUDED.calculated_at
            """,
            (kpi_id, period, value, datetime.now(timezone.utc)),
        )


def refresh_kpis_from_transactions() -> bool:
    """Recalculate materialized KPIs when normalized ERP data exists."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM transactions LIMIT 1)")
            has_transactions = bool(cursor.fetchone()[0])
            if has_transactions:
                _refresh_kpis(cursor)
                conn.commit()
            return has_transactions


def ingest_file(file_name: str, content: bytes, source_type: str = "erp") -> Dict[str, Any]:
    if source_type not in ("erp", "banco"):
        raise ValueError("source_type debe ser erp o banco")
    rows = extract_rows(file_name, content)
    if not rows:
        raise ValueError("El archivo no contiene filas financieras")
    for row in rows:
        row["source_reference"] = "%s:%s" % (Path(file_name).name, row["source_reference"])

    started = datetime.now(timezone.utc)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            data_source_id = _source_id(cursor, source_type, file_name)
            cursor.execute(
                "INSERT INTO sync_logs (data_source_id, started_at, status, rows_ingested) VALUES (%s, %s, 'en_proceso', 0) RETURNING id",
                (data_source_id, started),
            )
            sync_log_id = cursor.fetchone()[0]
            staging_table = "staging_bank_raw" if source_type == "banco" else "staging_erp_raw"
            for row in rows:
                payload = {key: _json_value(value) for key, value in row.items()}
                cursor.execute(
                    "INSERT INTO %s (sync_log_id, raw_payload, ingested_at) VALUES (%%s, %%s::jsonb, %%s)" % staging_table,
                    (sync_log_id, json.dumps(payload), started),
                )
                _upsert_transaction(cursor, row, source_type)
            _refresh_kpis(cursor)
            cursor.execute(
                "UPDATE sync_logs SET finished_at = %s, status = 'exitoso', rows_ingested = %s WHERE id = %s",
                (datetime.now(timezone.utc), len(rows), sync_log_id),
            )
            conn.commit()
    return {"sync_log_id": sync_log_id, "data_source_id": data_source_id, "rows_ingested": len(rows), "status": "exitoso"}
