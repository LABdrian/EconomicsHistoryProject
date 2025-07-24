# PostPunk ETL - Plataforma de Búsqueda de Bandas Post-Punk (1980-1999)

## Descripción
Monorepo 100% gratuito que ingesta datos abiertos sobre bandas post-punk, los procesa con Spark, y expone una plataforma web de búsqueda.

## Stack Tecnológico (todo OSS/gratuito)
- **Python 3.11** - Lenguaje principal
- **Apache Airflow 2.9** - Orquestación de datos (KubernetesExecutor)
- **Apache Spark 3.5** - Procesamiento distribuido (Spark-Operator)
- **MeiliSearch v1.8** - Motor de búsqueda full-text (MIT)
- **MongoDB Community 7** - Base de datos para documentos raw/normalizados
- **MinIO** - Almacenamiento S3 local
- **FastAPI 0.111** - API backend
- **React 18** - Frontend (Vite + Tailwind)
- **Kind + Helm v3** - Orquestación local Kubernetes
- **GitHub Actions** - CI/CD

## Fuentes de Datos (APIs gratuitas)
1. **MusicBrainz API** - Bandas, álbumes, tracks, miembros
2. **TheAudioDB API** - Top tracks y biografías
3. **Discogs API** - Metadata adicional (requiere key gratuita)

## Estructura del Proyecto
```
/postpunk-etl/
├─ dags/postpunk_etl.py          # DAG principal de Airflow
├─ jobs/normalize_bands.py       # Job de Spark para normalización
├─ api/main.py                   # FastAPI backend
├─ web/src/App.jsx              # Frontend React
├─ charts/{airflow,mongo,meili,postpunk-web}/  # Helm charts
├─ .github/workflows/ci-cd.yml  # Pipeline CI/CD
└─ README.md
```

## Instalación y Ejecución

### Prerrequisitos
- Kind (Kubernetes local)
- Helm v3
- Docker

### Setup Local
```bash
# 1. Crear cluster Kind
kind create cluster --name postpunk

# 2. Instalar charts
helm install airflow charts/airflow/
helm install mongodb charts/mongo/
helm install meilisearch charts/meili/
helm install postpunk-web charts/postpunk-web/

# 3. Configurar ingress
echo "127.0.0.1 postpunk.local" >> /etc/hosts
```

### Uso
1. Acceder a Airflow: `http://postpunk.local/airflow`
2. Ejecutar DAG `postpunk_etl`
3. Buscar bandas: `http://postpunk.local`

## API Endpoints
- `GET /search?q={query}` - Búsqueda de bandas/álbumes/canciones
- `GET /search?q={query}&filter=band` - Filtrar por banda
- `GET /search?q={query}&year={year}` - Filtrar por año

## Esquema de Datos
```sql
id | source | band | country | year_start | year_end | album | release_date | member | role | track | hit_rank | description
```

## Contribución
1. Fork del repo
2. Crear feature branch
3. Commit changes
4. Push to branch
5. Crear Pull Request

## Licencia
MIT - Ver archivo LICENSE para detalles