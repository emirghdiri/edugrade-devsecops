-- Schéma EduGrade (idempotent : peut être rejoué au démarrage).

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('student', 'teacher'))
);

CREATE TABLE IF NOT EXISTS grades (
    id         SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    subject    TEXT NOT NULL,
    value      NUMERIC(4, 2) NOT NULL CHECK (value >= 0 AND value <= 20),
    date       DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX IF NOT EXISTS idx_grades_student_id ON grades (student_id);

-- Matières proposées dans les formulaires (gérées par les enseignants).
CREATE TABLE IF NOT EXISTS subjects (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 2 AND 60)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_subjects_name ON subjects (lower(name));
