# ADR 0006: Autenticación JWT y Control de Acceso Basado en Roles (RBAC)

## Estado
Aprobado

## Contexto
El enunciado de la prueba de desempeño exige en múltiples secciones (Páginas 2, 3, 5, 6 y 7):
1. Ningún endpoint de datos accesible sin sesión previa (código HTTP 401).
2. Modelo estricto de roles: `viewer` vs `admin`.
3. Un usuario `viewer` no debe poder ejecutar acciones de administrador ni ver botones restringidos, y la API debe responder con HTTP 403 si intenta una invocación directa.
4. Credenciales del usuario administrador sembradas exclusivamente desde variables de entorno (`.env`), nunca en el código.
5. Emisión de tokens de acceso criptográficos (JWT).

## Decisión
1. **Estándar Criptográfico:**
   - Se utiliza **JSON Web Tokens (JWT)** con algoritmo `HS256` (HMAC con SHA-256).
   - La clave secreta `JWT_SECRET_KEY` se inyecta desde variables de entorno y se genera de forma aleatoria y segura (`secrets.token_hex(32)`).
   - Tiempo de expiración configurado por variable de entorno (`ACCESS_TOKEN_EXPIRE_MINUTES`, por defecto 60 minutos).
2. **Estructura del Payload (Claims):**
   ```json
   {
     "sub": "user_id_or_email",
     "username": "admin",
     "role": "admin",
     "exp": 1730030000,
     "iat": 1730026400
   }
   ```
   - Incluir el `role` en el token permite validaciones ultrarrápidas en memoria en cada endpoint sin sobrecargar la base de datos con consultas de usuario repetitivas.
3. **Mecanismo de Verificación en FastAPI:**
   - Dependencia `get_current_user`: Valida la firma del token y vigencia temporal. Devuelve `401 Unauthorized` si no hay token o es inválido.
   - Dependencia `require_admin`: Verifica que `current_user.role == 'admin'`. Devuelve `403 Forbidden` inmediato para usuarios `viewer`.
4. **Sembrado Seguro de Credenciales (Seed):**
   - Las contraseñas se almacenan exclusivamente como hashes criptográficos mediante `passlib[bcrypt]`.
   - Al iniciar la API / contenedor, un script lee `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `VIEWER_USERNAME`, `VIEWER_PASSWORD` desde `.env` y crea/actualiza los usuarios en la tabla `audit.users`.
5. **Soporte para Streaming SSE:**
   - El endpoint de eventos en tiempo real (`GET /api/stream`) acepta autenticación vía header `Authorization: Bearer <token>` y vía query parameter `?token=<token>` para máxima compatibilidad con clientes `EventSource` nativos en navegadores.

## Consecuencias
- **Positivas:**
  - Cumplimiento exacto de los criterios de evaluación del PDF.
  - Protección absoluta contra acceso no autenticado.
  - Facilidad de testeo automatizado con Pytest simulando tokens de ambos roles.
- **Negativas:**
  - La revocación inmediata de un token emitido antes de su expiración requiere una lista negra en memoria o tabla de revocación si fuera necesario (para esta prueba, la expiración corta de 60m es más que suficiente).
