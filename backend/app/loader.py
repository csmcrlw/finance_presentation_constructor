from pathlib import Path
import sqlite3
import re
import pandas as pd
from sqlalchemy import create_engine, text

MAX_BYTES = 100 * 1000 * 1000

def load_file(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        raise ValueError("Файл отсутствует или пуст")
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Размер файла превышает 100 МБ")
    ext = path.suffix.lower()
    if ext == ".csv":
        try:
            return pd.read_csv(path, sep=None, engine="python", encoding="utf-8-sig")
        except UnicodeDecodeError:
            return pd.read_csv(path, sep=None, engine="python", encoding="cp1251")
    if ext == ".xlsx":
        return pd.read_excel(path, engine="openpyxl")
    if ext == ".sql":
        return load_sql_dump(path)
    raise ValueError("Поддерживаются CSV, XLSX и SQL-файлы")

def load_sql(database_url: str, query: str) -> pd.DataFrame:
    normalized = query.strip().rstrip(";").strip()
    if not normalized.lower().startswith(("select ", "with ")) or ";" in normalized:
        raise ValueError("Разрешен только один запрос SELECT или WITH")
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            return pd.read_sql_query(text(normalized), connection)
    finally:
        engine.dispose()


def load_sql_dump(path: Path) -> pd.DataFrame:
    try:
        source = path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("SQL-файл должен быть в кодировке UTF-8") from exc
    if not source.strip():
        raise ValueError("SQL-файл пуст")

    statements = []
    buffer = ""
    for line in source.splitlines(keepends=True):
        buffer += line + "\n"
        if sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip() and not buffer.lstrip().startswith("--"):
        raise ValueError("Незавершенная SQL-команда")
    if len(statements) > 10000:
        raise ValueError("Слишком много SQL-команд")
    if not statements:
        raise ValueError("SQL-файл не содержит команд")

    permitted = re.compile(r"^\s*(?:--[^\n]*\n\s*)*(?:CREATE\s+TABLE\s+|INSERT\s+INTO\s+)", re.I)
    connection = sqlite3.connect(":memory:")
    try:
        connection.set_authorizer(lambda action, a1, a2, db, origin:
            sqlite3.SQLITE_DENY if action in {
                sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
                sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_DROP_TRIGGER,
                sqlite3.SQLITE_CREATE_TRIGGER, sqlite3.SQLITE_ALTER_TABLE,
                sqlite3.SQLITE_PRAGMA, sqlite3.SQLITE_CREATE_VTABLE,
            } else sqlite3.SQLITE_OK)
        for statement in statements:
            if not permitted.match(statement):
                raise ValueError("В SQL-файле разрешены только CREATE TABLE и INSERT INTO")
            try:
                connection.execute(statement)
            except sqlite3.Error as exc:
                raise ValueError(f"Не удалось прочитать SQL-файл: {exc}") from exc
        tables = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        required = {"period", "category", "plan", "fact"}
        matches = []
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            columns = {item[0].lower() for item in connection.execute(f"SELECT * FROM {quoted} LIMIT 0").description}
            if required.issubset(columns):
                matches.append(quoted)
        if len(matches) != 1:
            raise ValueError("SQL-файл должен содержать ровно одну таблицу с полями period, category, plan, fact")
        return pd.read_sql_query(f"SELECT * FROM {matches[0]}", connection)
    finally:
        connection.close()
