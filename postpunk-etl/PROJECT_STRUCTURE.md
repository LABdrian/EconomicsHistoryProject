# PostPunk ETL - Estructura del Proyecto

## Tabla de Archivos del Proyecto

| Archivo | Descripción |
|---------|-------------|
| **`README.md`** | Documentación principal del proyecto en español |
| **`Dockerfile`** | Imagen Docker multi-stage (API + Web) |
| **`requirements.txt`** | Dependencias Python para Airflow, Spark, FastAPI |
| | |
| **DAGs de Airflow** | |
| **`dags/postpunk_etl.py`** | DAG principal: extrae de MusicBrainz, TheAudioDB, Discogs |
| | |
| **Jobs de Spark** | |
| **`jobs/normalize_bands.py`** | Normaliza datos y carga a MongoDB + MeiliSearch |
| | |
| **API FastAPI** | |
| **`api/main.py`** | Backend con endpoints de búsqueda y serve de archivos estáticos |
| | |
| **Frontend React** | |
| **`web/package.json`** | Dependencias React + Vite + Tailwind |
| **`web/vite.config.js`** | Configuración de Vite |
| **`web/index.html`** | Template HTML principal |
| **`web/src/main.jsx`** | Punto de entrada React |
| **`web/src/App.jsx`** | Componente principal con búsqueda y filtros |
| **`web/src/index.css`** | Estilos Tailwind CSS |
| **`web/tailwind.config.js`** | Configuración Tailwind |
| **`web/postcss.config.js`** | Configuración PostCSS |
| | |
| **Helm Charts** | |
| **`charts/postpunk-web/Chart.yaml`** | Chart para aplicación web |
| **`charts/postpunk-web/values.yaml`** | Valores por defecto |
| **`charts/postpunk-web/templates/deployment.yaml`** | Template de Deployment |
| **`charts/postpunk-web/templates/service.yaml`** | Template de Service |
| **`charts/postpunk-web/templates/ingress.yaml`** | Template de Ingress |
| **`charts/postpunk-web/templates/_helpers.tpl`** | Helpers de Helm |
| **`charts/airflow/Chart.yaml`** | Chart para Apache Airflow |
| **`charts/airflow/values.yaml`** | Configuración Airflow con KubernetesExecutor |
| **`charts/meili/Chart.yaml`** | Chart para MeiliSearch |
| **`charts/meili/values.yaml`** | Configuración MeiliSearch |
| **`charts/mongo/Chart.yaml`** | Chart para MongoDB |
| **`charts/mongo/values.yaml`** | Configuración MongoDB Community |
| | |
| **CI/CD** | |
| **`.github/workflows/ci-cd.yml`** | Pipeline completo: lint, test, build, deploy |

## Funcionalidades Implementadas

### ✅ Extracción de Datos (Airflow DAG)
- **MusicBrainz API**: Bandas, álbumes, miembros (1980-1999)
- **TheAudioDB API**: Biografías y datos adicionales
- **Discogs API**: Metadata de releases
- Almacenamiento en MinIO (S3 local)

### ✅ Procesamiento de Datos (Spark)
- Normalización a esquema estándar
- Limpieza y deduplicación
- Carga a MongoDB (raw data)
- Indexación en MeiliSearch (full-text search)

### ✅ API de Búsqueda (FastAPI)
- `/api/search?q=` - Búsqueda principal
- `/api/bands/autocomplete` - Autocompletado
- `/api/stats` - Estadísticas de la base de datos
- `/api/health` - Health check
- Servir frontend estático

### ✅ Frontend (React)
- Interfaz moderna con Tailwind CSS
- Búsqueda en tiempo real
- Filtros por tipo, año, país, fuente
- Autocompletado de bandas
- UI responsive con tema dark

### ✅ Deployment (Kubernetes + Helm)
- Charts para todos los servicios
- Configuración para Kind (local)
- Ingress con nginx para postpunk.local
- Health checks y resource limits

### ✅ CI/CD (GitHub Actions)
- Lint de código Python y JavaScript
- Tests automatizados
- Build y push a GHCR
- Deploy automático a Kubernetes

## Comandos de Instalación

```bash
# 1. Crear cluster Kind
kind create cluster --name postpunk

# 2. Instalar todos los charts
helm install airflow charts/airflow/
helm install mongodb charts/mongo/
helm install meilisearch charts/meili/
helm install postpunk-web charts/postpunk-web/

# 3. Configurar hosts
echo "127.0.0.1 postpunk.local" >> /etc/hosts

# 4. Acceder a la aplicación
# - Frontend: http://postpunk.local
# - API: http://postpunk.local/api/docs
# - Airflow: http://postpunk.local/airflow
```

## Stack Tecnológico (100% Gratuito)

- **Apache Airflow 2.9** - Orquestación ETL
- **Apache Spark 3.5** - Procesamiento distribuido
- **MeiliSearch v1.8** - Motor de búsqueda full-text
- **MongoDB Community 7** - Base de datos NoSQL
- **MinIO** - S3 local para almacenamiento
- **FastAPI 0.111** - API backend moderna
- **React 18** - Frontend moderno
- **Vite + Tailwind** - Build tool y CSS framework
- **Kind + Helm v3** - Kubernetes local
- **GitHub Actions** - CI/CD pipeline

¡Proyecto completado! 🎸 ¡Disfruta explorando el universo post-punk!