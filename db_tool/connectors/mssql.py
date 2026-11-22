"""SQL Server connector. Tries pyodbc first, then pymssql."""

from .base import BaseConnector


class MSSQLConnector(BaseConnector):
    def _driver(self):
        try:
            import pyodbc
            return "pyodbc", pyodbc
        except ImportError:
            try:
                import pymssql
                return "pymssql", pymssql
            except ImportError:
                raise RuntimeError(
                    "Aucun driver SQL Server disponible. Installez pyodbc (avec le driver ODBC) ou pymssql."
                )

    def connect(self):
        kind, mod = self._driver()
        if kind == "pyodbc":
            conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={self.host},{self.port or 1433};"
                f"DATABASE={self.database};"
                f"UID={self.username};PWD={self.password};"
                f"TrustServerCertificate=yes;"
            )
            self._conn = mod.connect(conn_str, timeout=10)
            self._kind = kind
        else:
            self._conn = mod.connect(
                server=self.host,
                port=self.port or 1433,
                database=self.database,
                user=self.username,
                password=self.password,
                timeout=10,
            )
            self._kind = kind

    def test(self):
        try:
            self.connect()
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True, "Connexion SQL Server réussie"
        except Exception as e:
            return False, str(e)
        finally:
            self.close()

    def execute_query(self, sql):
        self.connect()
        try:
            cur = self._conn.cursor()
            cur.execute(sql)
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = []
            for r in cur.fetchall():
                rows.append({cols[i]: r[i] for i in range(len(cols))})
            cur.close()
            return rows
        finally:
            self.close()

    def close(self):
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
