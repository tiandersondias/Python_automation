-- Compatibility entry point for psql users.
-- The versioned files in ../migrations/ are the single source of truth.
-- Prefer `python migrate.py` for existing databases.
\set ON_ERROR_STOP on
\ir ../migrations/001_initial.sql
\ir ../migrations/002_data_quality_constraints.sql
\ir ../migrations/003_audit_history.sql
\ir ../migrations/004_validate_data_quality_constraints.sql
\ir ../migrations/005_audit_security.sql
\ir ../migrations/006_write_data_quality.sql
