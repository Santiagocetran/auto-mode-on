# Deploy — Halketon

Docker Compose para levantar **API** y **dashboard** en local. La base de datos y auth viven en **Supabase remoto** (no se levanta Postgres ni Kong en Docker).

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **dashboard** | [localhost:3000](http://localhost:3000) | Next.js user dashboard |
| **api** | [localhost:8000](http://localhost:8000) | FastAPI (`/health`, webhooks WhatsApp) |

## Requisitos

- Docker Desktop o Docker Engine + Compose v2
- Proyecto Supabase remoto con schema + seeds ya aplicados (`database/schema.sql`, `seeds.sql`, `seeds-auth.sql` vía SQL editor del equipo backend)
- Si la base se creó **antes** del confirmation gate de WhatsApp, aplicar también las migraciones incrementales en orden:
  - `database/migrations/001_chatbot_proactivity.sql`
  - `database/migrations/002_confirmation_gate.sql` (columna `resolved_task`, estado `awaiting_confirmation`)

  ```bash
  DATABASE_URL='postgresql://...' ./database/apply-migration.sh 002_confirmation_gate.sql
  ```

  O pegar el contenido del `.sql` en el SQL Editor de Supabase.

## Inicio rápido

```bash
cd deploy
cp .env.example .env
# Completar SUPABASE_URL, SUPABASE_ANON_KEY y SUPABASE_SERVICE_ROLE_KEY
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

- **Dashboard:** http://localhost:3000  
- **API health:** http://localhost:8000/health  

Usuarios demo (si corriste `seeds-auth.sql` en Supabase):

| Email | Password | Rol |
|-------|----------|-----|
| `admin@esperanza.org` | `admin` | owner |
| `user@esperanza.org` | `user` | member |

## Variables de entorno

| Variable | Uso |
|----------|-----|
| `SUPABASE_URL` | URL del proyecto (API + dashboard) |
| `SUPABASE_ANON_KEY` | Clave anon (auth en el navegador) |
| `SUPABASE_SERVICE_ROLE_KEY` | Lecturas/escrituras server-side |
| `OPENAI_API_KEY`, `TWILIO_*` | Opcionales para WhatsApp / LLM en la API |
| `PUBLIC_WEBHOOK_BASE_URL` | URL pública del API **sin** barra final (ej. `https://api.tudominio.com`). Twilio debe apuntar a `{PUBLIC_WEBHOOK_BASE_URL}/whatsapp`. Requerida en prod para validar la firma del webhook. |
| `SKIP_TWILIO_SIGNATURE_VALIDATION` | `true` solo en dev local con túnel. **Nunca** en prod/Coolify. |

Para exponer el webhook de Twilio al contenedor `api`, usa un túnel (`ngrok http 8000`), setea `PUBLIC_WEBHOOK_BASE_URL=https://<tunnel>` y apunta el sandbox a `https://<tunnel>/whatsapp`.

## Coolify

El `docker-compose.yml` **no** publica puertos en el host (3000/8000). Coolify enruta el tráfico por su proxy a los puertos internos del contenedor.

En la UI de Coolify, por servicio:

| Servicio | Puerto interno | Dominio (ejemplo) |
|----------|----------------|-------------------|
| **dashboard** | `3000` | `app.tudominio.com` |
| **api** | `8000` | `api.tudominio.com` |

Variables de entorno: las mismas de `.env.example` (`SUPABASE_URL`, claves, etc.).

En el servicio **api**, configurá obligatoriamente `PUBLIC_WEBHOOK_BASE_URL=https://api.tudominio.com` (el dominio que asignes en Coolify, sin barra final) y el webhook de Twilio en `{PUBLIC_WEBHOOK_BASE_URL}/whatsapp`.

Si el deploy falla con `port is already allocated`, suele haber un stack local levantado con el override:

```bash
cd deploy && docker compose -f docker-compose.yml -f docker-compose.local.yml down
```

## Comandos útiles

```bash
# Rebuild de una app (local con puertos en el host)
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build api
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build dashboard

# Detener stack local
docker compose -f docker-compose.yml -f docker-compose.local.yml down
```

## Desarrollo híbrido

Levantá solo una app en Docker y la otra en el host, o ninguna en Docker:

```bash
# Solo API en Docker (sin override = sin puertos en host; añade -f docker-compose.local.yml si necesitás localhost:8000)
docker compose up api

# Apps en el host (mismas credenciales de Supabase)
cd apps/api && uvicorn app.main:app --reload --port 8000
cd user-dashboard-design && bun run dev
```

Para desarrollo local sin Docker, usá `user-dashboard-design/.env.local` y `apps/api/.env` con las mismas variables de Supabase.

## Estructura

```
deploy/
├── docker-compose.yml
├── .env.example
└── docker/
    ├── api/Dockerfile
    └── dashboard/Dockerfile
```

Schema y seeds: `database/` en la raíz del repo — se aplican en el Supabase remoto, no desde este compose.
