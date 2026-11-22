"""PostgreSQL connector using psycopg2."""

from .base import BaseConnector


class PostgresConnector(BaseConnector):
    def connect(self):
        import psycopg2
        self._conn = psycopg2.connect(
            host=self.host,
            port=self.port or 5432,
            dbname=self.database,
            user=self.username,
            password=self.password,
            connect_timeout=10,
        )

    def test(self):
        try:
            self.connect()
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True, "Connexion PostgreSQL réussie"
        except Exception as e:
            return False, str(e)
        finally:
            self.close()

    def execute_query(self, sql):
        import psycopg2.extras
        self.connect()
        try:
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql)
            rows = [dict(r) for r in cur.fetchall()]
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
