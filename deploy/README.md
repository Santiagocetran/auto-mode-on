# Deploy — Halketon

Docker Compose para levantar **API** y **dashboard** en local. La base de datos y auth viven en **Supabase remoto** (no se levanta Postgres ni Kong en Docker).

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| **dashboard** | [localhost:3000](http://localhost:3000) | Next.js user dashboard |
| **api** | [localhost:8000](http://localhost:8000) | FastAPI (`/health`, webhooks WhatsApp) |

## Requisitos

- Docker Desktop o Docker Engine + Compose v2
- Proyecto Supabase remoto con schema + seeds ya aplicados (`database/schema.sql`, `seeds.sql`, `seeds-auth.sql` vía SQL editor del equipo backend)

## Inicio rápido

```bash
cd deploy
cp .env.example .env
# Completar SUPABASE_URL, SUPABASE_ANON_KEY y SUPABASE_SERVICE_ROLE_KEY
docker compose up --build
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

Para exponer el webhook de Twilio al contenedor `api`, usa un túnel (`ngrok http 8000`) y apunta el sandbox a `https://<tunnel>/whatsapp/...`.

## Comandos útiles

```bash
# Rebuild de una app
docker compose up --build api
docker compose up --build dashboard

# Detener
docker compose down
```

## Desarrollo híbrido

Levantá solo una app en Docker y la otra en el host, o ninguna en Docker:

```bash
# Solo API en Docker
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
