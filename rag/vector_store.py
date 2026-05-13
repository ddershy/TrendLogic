from __future__ import annotations

from .config import rag_config


class LanceDBVectorStore:
    def __init__(self, uri: str | None = None, table_name: str | None = None) -> None:
        try:
            import lancedb
        except ImportError as exc:
            raise RuntimeError("缺少 lancedb 依赖，请先安装 backend/requirements.txt。") from exc

        self.uri = uri or rag_config.lancedb_uri
        self.table_name = table_name or rag_config.lancedb_table
        self.db = lancedb.connect(self.uri)

    def add_many(self, records: list[dict], replace_document_id: str | None = None) -> None:
        if not records:
            return
        if self._table_exists():
            table = self.db.open_table(self.table_name)
            if replace_document_id:
                table.delete(_where_equals("document_id", replace_document_id))
            table.add(records)
            return
        self.db.create_table(self.table_name, data=records)

    def delete_document(self, document_id: str) -> None:
        if not document_id or not self._table_exists():
            return
        self.db.open_table(self.table_name).delete(_where_equals("document_id", document_id))

    def search(self, vector: list[float], top_k: int = 5, filters: dict | None = None) -> list[dict]:
        if not self._table_exists():
            return []
        table = self.db.open_table(self.table_name)
        query = table.search(vector)
        where_clause = _build_where_clause(filters or {})
        if where_clause:
            query = query.where(where_clause)
        rows = query.limit(max(1, int(top_k or 5))).to_list()
        return [_format_result(row) for row in rows]

    def _table_exists(self) -> bool:
        return self.table_name in self.db.table_names()


def _format_result(row: dict) -> dict:
    distance = float(row.get("_distance", 0.0) or 0.0)
    metadata = {
        "document_id": row.get("document_id"),
        "filename": row.get("filename"),
        "category": row.get("category"),
        "visibility": row.get("visibility"),
        "uploaded_by": row.get("uploaded_by"),
        "chunk_index": row.get("chunk_index"),
        "created_at": row.get("created_at"),
        "file_path": row.get("file_path"),
    }
    return {
        "text": row.get("text", ""),
        "metadata": {key: value for key, value in metadata.items() if value not in (None, "")},
        "score": 1 / (1 + distance),
    }


def _build_where_clause(filters: dict) -> str:
    allowed = {"document_id", "category", "visibility", "uploaded_by"}
    clauses = [_where_equals(key, str(value)) for key, value in filters.items() if key in allowed and value]
    return " AND ".join(clauses)


def _where_equals(key: str, value: str) -> str:
    escaped = value.replace("'", "''")
    return f"{key} = '{escaped}'"
