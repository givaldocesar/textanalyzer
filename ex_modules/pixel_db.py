import sqlite3 as sql


class PixelDataBase:
    def __init__(self):
        self.db = sql.connect(":memory:")
        self.db.row_factory = sql.Row
        self.cursor = self.db.cursor()

        self.cursor.execute('''CREATE TABLE pixels (
                                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                                x  INTEGER NOT NULL,
                                y  INTEGER NOT NULL,
                                textura REAL,
                                classe INTEGER);''')
        self.db.commit()

    def inserir(self, fields, values):
        command = 'INSERT INTO pixels ('
        command += ','.join(fields) + ') VALUES ('
        command += ','.join(values) + ')'
        self.cursor.execute(command)
        self.db.commit()

    def consultar(self, fields, where=None):
        command = 'SELECT '
        if fields == '*':
            command += fields
        else:
            command += ' (' + ','.join(fields) + ') '
        command += ' FROM pixels '

        if where:
            command += 'WHERE ' + where

        self.cursor.execute(command)
        result = self.cursor.fetchall()
        return result

    def atualizar_classe(self, classe, textura):
        command = 'UPDATE pixels SET classe = %s ' % classe
        command += 'WHERE textura = %s' % textura
        self.cursor.execute(command)
        self.db.commit()

