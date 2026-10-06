from __future__ import annotations

import sqlglot
import sqlglot.errors

class QueryValidationError(RuntimeError):
    def __init__(self, message: str, *, offending_part: str | None = None) -> None:
        super().__setattr__("message", message)
        super().__setattr__("offending_part", offending_part)

    @property
    def message(self) -> str:
        return self.args[0]  # type: ignore

    @property
    def offending_part(self) -> str | None:
        return getattr(self, "offending_part", None)


class QueryValidator:
    @staticmethod
    def validate_sql(sql: str, dialect: str = "postgres") -> str:
        stripped = sql.strip()
        if not stripped:
            raise QueryValidationError("SQL statement is empty after stripping.", offending_part=sql)

        # Normalize dialect for sqlglot
        sqlglot_dialect = dialect.lower()
        if sqlglot_dialect == "postgresql":
            sqlglot_dialect = "postgres"

        try:
            statements = sqlglot.parse(stripped, read=sqlglot_dialect)
            statements = [stmt for stmt in statements if stmt is not None]

            if not statements:
                raise QueryValidationError("No valid SQL statements found.", offending_part=sql)

            if len(statements) > 1:
                raise QueryValidationError("Multiple SQL statements detected. Only a single statement is allowed.", offending_part=sql)

            stmt = statements[0]

            if not isinstance(stmt, sqlglot.exp.Select):
                raise QueryValidationError(f"Query must be a SELECT statement (found: {stmt.key}).", offending_part=sql)

            return stmt.sql(dialect=sqlglot_dialect)

        except sqlglot.errors.ParseError as e:
            raise QueryValidationError(f"SQL parsing error: {e}", offending_part=sql)
