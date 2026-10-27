-- ==============================================================================
-- SismoWatch Database Initialization - Script 03: Seed Initial RBAC Users
-- ==============================================================================

-- 1. Seed Admin User (Credenciales por defecto sembradas según .env)
-- Usuario: admin / Clave: SismoAdmin2026!Secret
INSERT INTO audit.users (id, username, email, hashed_password, role, is_active)
VALUES (
    'a0000000-0000-0000-0000-000000000001',
    'admin',
    'admin@sismowatch.internal',
    '$2b$12$vctuDNH31UeZImyboNMntOjCsRBnkY1FXeTeLYB3eFmeGogPtSRGW',
    'admin',
    TRUE
)
ON CONFLICT (username) DO UPDATE 
SET hashed_password = EXCLUDED.hashed_password,
    role = 'admin',
    is_active = TRUE;

-- 2. Seed Viewer User (Solo Lectura)
-- Usuario: viewer / Clave: SismoViewer2026!
INSERT INTO audit.users (id, username, email, hashed_password, role, is_active)
VALUES (
    'b0000000-0000-0000-0000-000000000002',
    'viewer',
    'viewer@sismowatch.internal',
    '$2b$12$RQhea/eBTt2Lz6fFvANBwumV/O4bJPJt/yvIWjTfvvF3m3Md9ORTK',
    'viewer',
    TRUE
)
ON CONFLICT (username) DO UPDATE 
SET hashed_password = EXCLUDED.hashed_password,
    role = 'viewer',
    is_active = TRUE;
