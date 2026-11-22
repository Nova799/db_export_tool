"""MySQL connector using pymysql."""

from .base import BaseConnector


class MySQLConnector(BaseConnector):
    def connect(self):
        import pymysql
        self._conn = pymysql.connect(
            host=self.host,
            port=self.port or 3306,
            database=self.database,
            user=self.username,
            password=self.password,
            connect_timeout=10,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def test(self):
        try:
            self.connect()
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return True, "Connexion MySQL réussie"
        except Exception as e:
            return False, str(e)
        finally:
            self.close()

    def execute_query(self, sql):
        self.connect()
        try:
            cur = self._conn.cursor()
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
