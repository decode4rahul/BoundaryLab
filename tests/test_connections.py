import sqlite3
import tempfile
import unittest
from storage import Store

class ConnectionLifecycleTests(unittest.TestCase):
    def test_connection_closed_after_commit(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root)
            with store.connect() as db:
                db.execute('CREATE TABLE lifecycle_test (value TEXT)')
                db.execute('INSERT INTO lifecycle_test VALUES (?)',('committed',))
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            with store.connect() as check:
                self.assertEqual(check.execute('SELECT value FROM lifecycle_test').fetchone()[0],'committed')
    def test_connection_closed_and_transaction_rolled_back_after_error(self):
        with tempfile.TemporaryDirectory() as root:
            store=Store(root)
            with store.connect() as db:db.execute('CREATE TABLE lifecycle_test (value TEXT)')
            with self.assertRaises(RuntimeError):
                with store.connect() as db:
                    db.execute('INSERT INTO lifecycle_test VALUES (?)',('must roll back',))
                    raise RuntimeError('simulated interruption')
            with self.assertRaises(sqlite3.ProgrammingError):db.execute('SELECT 1')
            with store.connect() as check:
                self.assertEqual(check.execute('SELECT COUNT(*) FROM lifecycle_test').fetchone()[0],0)
