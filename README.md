# Sistema Multiagente con LangGraph — API Asíncrona, Redis, HITL y Observabilidad

Proyecto desarrollado en Python con LangGraph para implementar un sistema multiagente con API REST asíncrona, persistencia en Redis, Human-in-the-loop (HITL), integración con un LLM real mediante Google Gemini y observabilidad con LangSmith.

## Características principales

El sistema implementa:

- arquitectura multiagente con LangGraph;
- Supervisor para controlar el flujo;
- Research Agent conectado a Google Gemini;
- Analyst Agent para procesamiento posterior;
- nodo de aprobación humana;
- pausa real mediante `interrupt()`;
- reanudación mediante `Command(resume=...)`;
- persistencia de checkpoints de LangGraph en Redis;
- persistencia independiente del estado de jobs en Redis;
- API REST con FastAPI;
- procesamiento en segundo plano;
- estados `PENDING`, `RUNNING`, `WAITING_APPROVAL`, `DONE`, `FAILED` y `REJECTED`;
- manejo de errores del worker;
- trazas reales en LangSmith;
- registro de tokens, costo y latencia del LLM;
- prueba reproducible con 5 solicitudes concurrentes;
- cálculo de latencia p95.

---

## Arquitectura

El flujo general es:

```text
Cliente
   |
   v
FastAPI
POST /tasks
   |
   +--> Redis: estado del job
   |
   +--> Worker asíncrono
            |
            v
        LangGraph
            |
            v
       Supervisor
            |
            v
      Research Agent
            |
            v
    Google Gemini 3.6 Flash
            |
            v
       Supervisor
            |
            v
       Analyst Agent
            |
            v
       Supervisor
            |
            v
       Approval Node
          /      \
         /        \
 no crítico      crítico
    |               |
    v               v
Validation      interrupt()
    |               |
    v         WAITING_APPROVAL
   DONE             |
                    v
          POST /tasks/{id}/approve
                    |
                    v
          Command(resume=...)
                    |
              +-----+-----+
              |           |
           aprobado    rechazado
              |           |
              v           v
         Validation    REJECTED
              |
              v
             DONE
```

---

## Agentes y nodos

### Supervisor

Analiza el estado compartido y decide qué nodo debe ejecutarse a continuación.

### Research Agent

Recibe la consulta y realiza una llamada real al modelo:

```text
gemini-3.6-flash
```

La respuesta del LLM se almacena en:

```text
research_result
```

Las llamadas quedan registradas en LangSmith junto con:

- input tokens;
- output tokens;
- total tokens;
- duración;
- costo calculado por la plataforma.

### Analyst Agent

Procesa el resultado de investigación y extrae conceptos principales mediante una herramienta local.

El resultado se almacena en:

```text
analysis_result
```

### Approval Node

Determina si una tarea necesita aprobación humana.

Para las pruebas del proyecto, una consulta que contenga:

```text
[critical]
```

activa el flujo HITL.

En ese caso LangGraph ejecuta:

```python
interrupt(...)
```

y el job queda en:

```text
WAITING_APPROVAL
```

### Validation Node

Comprueba que existan resultados suficientes y genera la respuesta final del sistema.

---

## Estados de los jobs

Los estados utilizados son:

```text
PENDING
RUNNING
WAITING_APPROVAL
DONE
FAILED
REJECTED
```

### PENDING

El job fue creado pero todavía no comenzó a ejecutarse.

### RUNNING

El worker está procesando el grafo.

### WAITING_APPROVAL

LangGraph fue pausado mediante `interrupt()` y espera una decisión externa.

### DONE

La tarea finalizó correctamente.

### FAILED

Ocurrió una excepción durante el procesamiento.

### REJECTED

La operación fue rechazada por aprobación humana.

---

## Redis

Redis cumple dos responsabilidades diferentes.

### 1. Estado de jobs

Se almacenan datos como:

```text
job_id
status
input
result
error
thread_id
created_at
updated_at
started_at
finished_at
```

Las claves utilizan el formato:

```text
job:{job_id}
```

### 2. Checkpoints de LangGraph

LangGraph utiliza:

```text
AsyncRedisSaver
```

para persistir su estado interno.

Esto permite que una ejecución pausada por HITL pueda reanudarse utilizando el mismo:

```text
thread_id
```

incluso después de reiniciar la API.

---

## Requisitos

- Windows 10/11
- PowerShell
- Python 3.12+
- Redis compatible con Redis Search y RedisJSON
- API key de Google Gemini
- cuenta de LangSmith para observabilidad

Versiones verificadas durante el desarrollo:

```text
Python 3.12.10
LangGraph 1.2.11
langgraph-checkpoint 4.2.0
langgraph-checkpoint-redis 0.5.2
redis 8.1.0
FastAPI 0.141.1
Uvicorn 0.52.0
HTTPX 0.28.1
LangSmith 0.12.6
langchain-google-genai 4.4.0
Pydantic 2.13.5
```

---

## Instalación

### 1. Clonar el repositorio

```powershell
git clone https://github.com/agustingggutierrez/sistema-multiagente-langgraph.git
cd sistema-multiagente-langgraph
```

### 2. Crear entorno virtual

```powershell
py -3.12 -m venv .venv
```

### 3. Activar entorno virtual

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Instalar dependencias

```powershell
python -m pip install -r requirements.txt
```

---

## Variables de entorno

El repositorio contiene:

```text
.env.example
```

como referencia.

Las claves reales NO deben subirse al repositorio.

El proyecto lee las variables desde el entorno del sistema o de PowerShell.

### Redis

```powershell
$env:REDIS_URL="redis://127.0.0.1:6380"
```

### Google Gemini

```powershell
$geminiKey = Read-Host "API key de Gemini" -AsSecureString
$env:GOOGLE_API_KEY = [System.Net.NetworkCredential]::new("", $geminiKey).Password
```

### LangSmith

```powershell
$langsmithKey = Read-Host "API key de LangSmith" -AsSecureString
$env:LANGSMITH_API_KEY = [System.Net.NetworkCredential]::new("", $langsmithKey).Password

$env:LANGSMITH_TRACING="true"
$env:LANGSMITH_PROJECT="pre-entrega-7-langgraph"
```

Verificación sin mostrar secretos:

```powershell
Write-Host "Gemini:" (-not [string]::IsNullOrWhiteSpace($env:GOOGLE_API_KEY))
Write-Host "LangSmith:" (-not [string]::IsNullOrWhiteSpace($env:LANGSMITH_API_KEY))
```

---

## Redis local

El proyecto necesita una instancia Redis con soporte para:

- Redis Search;
- RedisJSON.

Durante el desarrollo se utilizó Redis 8.10.2 dentro de WSL Ubuntu en:

```text
redis://127.0.0.1:6380
```

En el entorno utilizado durante el desarrollo se inicia con:

```powershell
wsl -d Ubuntu -- bash -lc 'cd ~/redis-build/redis-8.10.2 && ./src/redis-server --port 6380 --daemonize yes --loadmodule ./modules/redisearch/redisearch.so --loadmodule ./modules/redisjson/rejson.so'
```

Comprobar conexión:

```powershell
wsl -d Ubuntu -- redis-cli -p 6380 PING
```

Resultado esperado:

```text
PONG
```

También puede utilizarse cualquier instancia Redis compatible configurando correctamente:

```text
REDIS_URL
```

---

## Iniciar la API

Con Redis activo y las variables de entorno configuradas:

```powershell
python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

Resultado esperado:

```text
Uvicorn running on http://127.0.0.1:8000
```

Swagger queda disponible en:

```text
http://127.0.0.1:8000/docs
```

---

## Endpoints

### GET /health

Comprueba la API y la conexión con Redis.

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

---

### POST /tasks

Crea un nuevo job y devuelve inmediatamente su identificador.

```powershell
$body = @{
    query = "Explica que es LangGraph"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/tasks" `
    -ContentType "application/json" `
    -Body $body
```

Respuesta inicial esperada:

```json
{
  "job_id": "...",
  "thread_id": "...",
  "status": "PENDING"
}
```

La ejecución continúa en segundo plano.

---

### GET /tasks/{job_id}

Permite consultar el estado:

```powershell
Invoke-RestMethod `
    -Method Get `
    -Uri "http://127.0.0.1:8000/tasks/JOB_ID"
```

Los estados posibles son:

```text
PENDING
RUNNING
WAITING_APPROVAL
DONE
FAILED
REJECTED
```

---

## Human-in-the-loop

Para activar una tarea crítica:

```powershell
$body = @{
    query = "[critical] Autorizar esta operacion"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/tasks" `
    -ContentType "application/json" `
    -Body $body
```

El job debe alcanzar:

```text
WAITING_APPROVAL
```

### Aprobar

```powershell
$approval = @{
    approved = $true
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri "http://127.0.0.1:8000/tasks/JOB_ID/approve" `
    -ContentType "application/json" `
    -Body $approval
```

LangGraph reanuda el checkpoint real utilizando el mismo `thread_id`.

### Rechazar

```powershell
$approval = @{
    approved = $false
} | ConvertTo-Json
```

El job finaliza en:

```text
REJECTED
```

---

## Manejo de errores

Si ocurre una excepción dentro del worker:

```text
RUNNING
   |
   v
FAILED
```

Redis almacena el error y los timestamps correspondientes.

La API también maneja:

- job inexistente → HTTP 404;
- job que no espera aprobación → HTTP 409;
- Redis no disponible → HTTP 503;
- errores del grafo;
- errores del LLM;
- errores del worker.

---

## Prueba de 5 solicitudes concurrentes

El proyecto incluye:

```text
load_test.py
```

La prueba utiliza:

```text
asyncio
httpx.AsyncClient
```

Ejecutar con la API activa:

```powershell
python .\load_test.py
```

El script:

1. envía 5 solicitudes concurrentemente;
2. registra los `job_id`;
3. consulta sus estados;
4. espera su finalización;
5. mide el tiempo de respuesta del POST;
6. mide el tiempo total de procesamiento;
7. calcula p95;
8. muestra los estados finales.

---

## Resultado real de prueba concurrente

En una ejecución verificada se obtuvo:

```text
Solicitudes: 5

POST promedio: 90.73 ms
POST mínimo: 56.81 ms
POST máximo: 155.99 ms
POST p95: 142.55 ms

Procesamiento promedio: 5985.36 ms
Procesamiento p95: 9041.52 ms

Tiempo total de la prueba concurrente: 10010.39 ms

Estados finales:
DONE
DONE
DONE
DONE
DONE
```

Esto demuestra que `POST /tasks` devuelve el identificador antes de finalizar el procesamiento completo.

---

## Observabilidad con LangSmith

Las ejecuciones de LangGraph quedan registradas en el proyecto:

```text
pre-entrega-7-langgraph
```

LangSmith permite visualizar:

- ejecución completa del grafo;
- Supervisor;
- Research Agent;
- Analyst Agent;
- Approval;
- Validation;
- llamada a `ChatGoogleGenerativeAI`;
- duración;
- input tokens;
- output tokens;
- total tokens;
- costo calculado por la plataforma;
- errores.

---

## LLM utilizado

El Research Agent utiliza:

```text
gemini-3.6-flash
```

Durante una prueba individual real se registraron:

```text
Input tokens: 65
Output tokens: 95
Total tokens: 160
```

LangSmith calcula el costo de las ejecuciones según su mapa de precios.

---

## Evidencias

Las capturas reales se encuentran en:

```text
screenshots/
```

### 01_traces_5_requests.png

Muestra las ejecuciones concurrentes registradas en LangSmith junto con:

- estado;
- duración;
- tokens;
- costo.

### 02_trace_detail_nodes_llm.png

Muestra el detalle de una ejecución y los nodos del grafo, incluyendo la llamada al LLM.

### 03_latency_p95.png

Muestra el resultado de la prueba concurrente y las métricas p95.

---

## Estructura principal

```text
sistema-multiagente-langgraph/
|
|-- agents/
|   |-- __init__.py
|   |-- research_agent.py
|   `-- analyst_agent.py
|
|-- api.py
|-- worker.py
|-- job_store.py
|-- graph.py
|-- state.py
|-- tools.py
|-- main.py
|-- load_test.py
|-- demo.ipynb
|-- generate_diagram.py
|-- graph.mmd
|-- graph.png
|
|-- screenshots/
|   |-- 01_traces_5_requests.png
|   |-- 02_trace_detail_nodes_llm.png
|   `-- 03_latency_p95.png
|
|-- requirements.txt
|-- .env.example
|-- .gitignore
`-- README.md
```

---

## Tecnologías utilizadas

- Python 3.12
- LangGraph
- LangChain
- Google Gemini
- FastAPI
- Uvicorn
- Redis
- Redis Search
- RedisJSON
- HTTPX
- asyncio
- Pydantic
- LangSmith
- WSL Ubuntu

---

## Seguridad

El repositorio no debe contener:

```text
.env
API keys
passwords
tokens privados
.venv
__pycache__
```

`.gitignore` protege los archivos y directorios locales.

`.env.example` contiene únicamente nombres de variables y ejemplos seguros.

---

## Limitación de la implementación

El procesamiento en segundo plano utiliza `asyncio.create_task()` dentro del proceso de FastAPI.

Esto permite que `POST /tasks` responda antes de que termine LangGraph.

En una arquitectura productiva distribuida podría reemplazarse por un sistema de colas externo como Celery, RQ o ARQ para obtener recuperación automática de jobs que estuvieran ejecutándose durante una caída completa del proceso.

Redis mantiene de forma persistente:

- estado de jobs;
- checkpoints de LangGraph;
- ejecuciones pausadas por HITL.

---

## Resultado

El sistema permite demostrar:

```text
POST /tasks
    |
    v
PENDING
    |
    v
RUNNING
    |
    v
LangGraph + Gemini
    |
    +--> DONE
    |
    +--> FAILED
    |
    `--> WAITING_APPROVAL
             |
             v
          /approve
         /        \
        v          v
      DONE      REJECTED
```

El flujo utiliza ejecuciones reales, persistencia real, llamadas reales al LLM y trazas reales de observabilidad.
