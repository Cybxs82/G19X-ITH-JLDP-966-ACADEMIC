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


def extract_raw_rows(file_name: str, content: bytes) -> List[Dict[str, Any]]:
    suffix = Path(file_name).suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        raw_rows = extract_excel(content)
    elif suffix == ".csv":
        raw_rows = extract_csv(content)
    elif suffix == ".pdf":
        raw_rows = extract_pdf(content)
    else:
        raise ValueError("Formato no soportado: %s" % suffix)
    return raw_rows


def extract_rows(file_name: str, content: bytes) -> List[Dict[str, Any]]:
    return [_canonical_row(row, index) for index, row in enumerate(extract_raw_rows(file_name, content), start=2)]


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _source_id(cursor: Any, source_type: str, file_name: str) -> int:
    cursor.execute(
        "SELECT id FROM fuentes_datos WHERE nombre = %s AND tipo = %s::fuente_tipo ORDER BY id LIMIT 1",
        (file_name, source_type),
    )
    existing = cursor.fetchone()
    if existing is not None:
        return existing[0]
    cursor.execute(
        """
        INSERT INTO fuentes_datos (nombre, tipo, configuracion_conexion, esta_activa)
        VALUES (%s, %s::fuente_tipo, %s::jsonb, TRUE)
        RETURNING id
        """,
        (file_name, source_type, json.dumps({"mode": "file", "file_name": file_name})),
    )
    return cursor.fetchone()[0]


def _upsert_transaction(cursor: Any, row: Dict[str, Any], source_type: str, data_source_id: int) -> None:
    cursor.execute(
        """
        INSERT INTO cuentas (codigo, nombre, categoria)
        VALUES (%s, %s, %s)
        ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre, categoria = EXCLUDED.categoria
        RETURNING id
        """,
        (row["account_code"], row["account_name"], row["category"]),
    )
    account_id = cursor.fetchone()[0]
    cursor.execute(
        """
        INSERT INTO centros_costo (codigo, nombre)
        VALUES (%s, %s)
        ON CONFLICT (codigo) DO UPDATE SET nombre = EXCLUDED.nombre
        RETURNING id
        """,
        (row["cost_center_code"], row["cost_center_name"]),
    )
    cost_center_id = cursor.fetchone()[0]
    cursor.execute(
        """
        INSERT INTO transacciones
            (cuenta_id, centro_costo_id, fuente_datos_id, tipo_fuente, referencia_fuente, monto, moneda, fecha_transaccion, descripcion)
        VALUES (%s, %s, %s, %s::fuente_tipo, %s, %s, %s, %s, %s)
        ON CONFLICT (fuente_datos_id, referencia_fuente) DO UPDATE SET
            cuenta_id = EXCLUDED.cuenta_id,
            centro_costo_id = EXCLUDED.centro_costo_id,
            monto = EXCLUDED.monto,
            moneda = EXCLUDED.moneda,
            fecha_transaccion = EXCLUDED.fecha_transaccion,
            descripcion = EXCLUDED.descripcion
        """,
        (account_id, cost_center_id, data_source_id, source_type, row["source_reference"], row["amount"], row["currency"], row["transaction_date"], row["description"]),
    )


def _refresh_kpis(cursor: Any) -> None:
    cursor.execute(
        """
         SELECT COALESCE(SUM(CASE WHEN t.monto > 0 THEN t.monto ELSE 0 END), 0),
             COALESCE(SUM(CASE WHEN t.monto < 0 THEN ABS(t.monto) ELSE 0 END), 0),
             COALESCE(SUM(t.monto), 0)
         FROM transacciones t
        """
    )
    income, expenses, net = [Decimal(str(value)) for value in cursor.fetchone()]
    liquidity = income / expenses if expenses else Decimal("0")
    margin = net / income * Decimal("100") if income else Decimal("0")
    cursor.execute("SELECT COALESCE(SUM(b.monto_presupuestado), 0) FROM presupuestos b")
    budget = Decimal(str(cursor.fetchone()[0]))
    deviation = ((expenses - budget) / budget * Decimal("100")) if budget else Decimal("0")
    values = [(1, liquidity), (2, margin), (3, income), (4, deviation)]
    period = date.today().replace(day=1)
    cursor.execute(
        "DELETE FROM valores_kpi WHERE definicion_kpi_id IN (1, 2, 3, 4) AND centro_costo_id IS NULL AND periodo = %s",
        (period,),
    )
    for kpi_id, value in values:
        cursor.execute(
            """
            INSERT INTO valores_kpi (definicion_kpi_id, centro_costo_id, periodo, valor, calculado_en)
            VALUES (%s, NULL, %s, %s, %s)
            ON CONFLICT (definicion_kpi_id, centro_costo_id, periodo) DO UPDATE SET valor = EXCLUDED.valor, calculado_en = EXCLUDED.calculado_en
            """,
            (kpi_id, period, value, datetime.now(timezone.utc)),
        )


def refresh_kpis_from_transactions() -> bool:
    """Recalculate materialized KPIs when normalized ERP data exists."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT EXISTS (SELECT 1 FROM transacciones LIMIT 1)")
            has_transactions = bool(cursor.fetchone()[0])
            if has_transactions:
                _refresh_kpis(cursor)
                conn.commit()
            return has_transactions


def ingest_file(file_name: str, content: bytes, source_type: str = "erp") -> Dict[str, Any]:
    if source_type not in ("erp", "banco"):
        raise ValueError("source_type debe ser erp o banco")
    raw_rows = extract_raw_rows(file_name, content)
    if not raw_rows:
        raise ValueError("El archivo no contiene filas financieras")
    rows: List[Dict[str, Any]] = []
    rejected_rows: List[Tuple[Dict[str, Any], str]] = []
    for index, raw_row in enumerate(raw_rows, start=2):
        try:
            row = _canonical_row(raw_row, index)
        except ValueError as error:
            rejected_rows.append((raw_row, str(error)))
            continue
        row["source_reference"] = "%s:%s" % (Path(file_name).name, row["source_reference"])
        rows.append(row)
    if not rows and rejected_rows:
        raise ValueError("Todas las filas fueron rechazadas durante la normalización")

    started = datetime.now(timezone.utc)
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            data_source_id = _source_id(cursor, source_type, file_name)
            cursor.execute(
                "INSERT INTO registros_sincronizacion (fuente_datos_id, iniciado_en, estado, filas_ingresadas) VALUES (%s, %s, 'en_proceso', 0) RETURNING id",
                (data_source_id, started),
            )
            sync_log_id = cursor.fetchone()[0]
            staging_table = "datos_temporales_banco" if source_type == "banco" else "datos_temporales_erp"
            for row in rows:
                payload = {key: _json_value(value) for key, value in row.items()}
                cursor.execute(
                    "INSERT INTO %s (registro_sincronizacion_id, carga_cruda, ingresado_en) VALUES (%%s, %%s::jsonb, %%s)" % staging_table,
                    (sync_log_id, json.dumps(payload), started),
                )
                _upsert_transaction(cursor, row, source_type, data_source_id)
            for raw_row, reason in rejected_rows:
                payload = {key: _json_value(value) for key, value in raw_row.items()}
                cursor.execute(
                    """
                    INSERT INTO registros_sincronizacion_rechazados
                        (registro_sincronizacion_id, carga_cruda, motivo_rechazo)
                    VALUES (%s, %s::jsonb, %s)
                    """,
                    (sync_log_id, json.dumps(payload), reason),
                )
            _refresh_kpis(cursor)
            cursor.execute(
                """
                UPDATE registros_sincronizacion
                SET finalizado_en = %s, estado = 'exitoso', filas_ingresadas = %s, filas_rechazadas = %s
                WHERE id = %s
                """,
                (datetime.now(timezone.utc), len(rows), len(rejected_rows), sync_log_id),
            )
            conn.commit()
    return {
        "sync_log_id": sync_log_id,
        "data_source_id": data_source_id,
        "rows_ingested": len(rows),
        "rows_rejected": len(rejected_rows),
        "status": "exitoso",
    }
