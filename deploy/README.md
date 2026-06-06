# Deploy local — Halketon

Docker Compose para levantar el stack completo en desarrollo:

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **dashboard** | [localhost:3000](http://localhost:3000) | Next.js user dashboard |
| **api** | [localhost:8000](http://localhost:8000) | FastAPI (`/health`, webhooks WhatsApp) |
| **kong** (Supabase API) | [localhost:54321](http://localhost:54321) | Gateway REST + Auth |
| **postgres** | `localhost:54322` | Base de datos (acceso directo) |

## Requisitos

- Docker Desktop o Docker Engine + Compose v2
- ~4 GB RAM libres para el build del dashboard

## Inicio rápido

```bash
cd deploy
cp .env.example .env
docker compose up --build
```

La primera vez tarda más: `db-init` aplica `database/schema.sql`, `seeds.sql`, grants y `seeds-auth.sql`.

### URLs y credenciales demo

- **Dashboard:** http://localhost:3000  
- **API health:** http://localhost:8000/health  
- **Supabase REST:** http://localhost:54321/rest/v1/

Usuarios de prueba (tras `seeds-auth.sql`):

| Email | Password | Rol |
|-------|----------|-----|
| `admin@esperanza.org` | `admin` | owner |
| `user@esperanza.org` | `user` | member |

## Variables de entorno

Copia `deploy/.env.example` → `deploy/.env`. Las claves `ANON_KEY` y `SERVICE_ROLE_KEY` son las de Supabase local estándar; no las cambies salvo que rotes `JWT_SECRET` (y regeneres los JWT).

Opcionales para probar WhatsApp / LLM en la API:

- `OPENAI_API_KEY`
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`

Para exponer el webhook de Twilio al contenedor `api`, usa un túnel hacia el host (`ngrok http 8000`) y apunta el sandbox a `https://<tunnel>/whatsapp/...`.

## Comandos útiles

```bash
# Solo infra (db + supabase local), sin apps
docker compose up db auth rest kong db-init

# Rebuild de una app
docker compose up --build api
docker compose up --build dashboard

# Reset completo de la base (borra datos)
docker compose down -v
docker compose up --build
```

## Desarrollo híbrido

Puedes levantar solo la infra y correr las apps en el host:

```bash
docker compose up db auth rest kong db-init
```

**API** (`apps/api/.env`):

```env
SUPABASE_URL=http://localhost:54321
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY de deploy/.env>
```

```bash
cd apps/api
uvicorn app.main:app --reload --port 8000
```

**Dashboard** (`user-dashboard-design/.env.local`):

```env
DATA_SOURCE=supabase
NEXT_PUBLIC_SUPABASE_URL=http://localhost:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=<ANON_KEY de deploy/.env>
SUPABASE_SERVICE_ROLE_KEY=<SERVICE_ROLE_KEY de deploy/.env>
DEMO_ORG_SLUG=fundacion-esperanza
```

```bash
cd user-dashboard-design
bun run dev
```

## Estructura

```
deploy/
├── docker-compose.yml      # Orquestación
├── .env.example            # Plantilla de secrets
├── docker/
│   ├── api/Dockerfile
│   └── dashboard/Dockerfile
├── kong/kong.yml           # Rutas /auth/v1 y /rest/v1
├── postgres/grants.sql     # Permisos PostgREST
└── scripts/init-db.sh      # Migración + seeds al primer arranque
```

Los SQL de dominio viven en `database/` en la raíz del repo; el deploy solo los monta y ejecuta.
