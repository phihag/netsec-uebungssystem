from __future__ import unicode_literals

import sqlite3

from .file import File
from .sheet import Sheet
from .submission import Submission
from .student import Student


class Database(object):
    def __init__(self, config):
        databasePath = config("database_path")
        self.database = sqlite3.connect(databasePath)
        self.cursor = self.database.cursor()
        self.createTables()

    def createTables(self):
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS `sheet` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `end` BIGINT,
                `deleted` boolean
            )""")
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS `task` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `sheet_id` INTEGER REFERENCES sheet(id),
                `name` text,
                `decipoints` INTEGER
            )""")
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS `submission` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `sheet_id` INTEGER REFERENCES sheet(id),
                `student_id` INTEGER REFERENCES student(id),
                `time` BIGINT,
                `files_path` text
            )""")
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS `grading` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `submission_id` INTEGER REFERENCES submission(id),
                `comment` TEXT,
                `time` BIGINT,
                `decipoints` INTEGER
            )""")
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS `file` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `submission_id` INTEGER REFERENCES submission(id),
                `hash` text,
                `filename` text
            )""")
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS `student` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT
            )""")
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS `alias` (
                `id` INTEGER PRIMARY KEY AUTOINCREMENT,
                `student_id` INTEGER REFERENCES student(id),
                `alias` text UNIQUE
            )""")

    def getSheets(self):
        self.cursor.execute("SELECT id, end, deleted FROM sheet")
        rows = self.cursor.fetchall()
        result = []

        for row in rows:
            id, end, deleted = row
            result.append(Sheet(id, end, deleted))

        return result

    def getStudent(self, identifier):
        aliases = self.getAliasesForStudent(identifier)
        return Student(identifier, aliases)

    def getStudents(self):
        self.cursor.execute("SELECT id FROM student")
        rows = self.cursor.fetchall()
        result = []

        for row in rows:
            student_id = row[0]
            aliases = self.getAliasesForStudent(student_id)
            result.append(Student(student_id, aliases))

        return result

    def getFilesForSubmission(self, submission_id):
        self.cursor.execute("SELECT id, hash, filename FROM file WHERE submission_id = ?", (submission_id, ))
        rows = self.cursor.fetchall()
        result = []

        for row in rows:
            id, hash, filename = row
            result.append(File(id, hash, filename))

        return result

    def commit(self):
        return self.database.commit()
