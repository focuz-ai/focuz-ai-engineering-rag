# Retrieval híbrido con aislamiento y vigencia

Autor: [Focuz](https://www.focuz.io/). Caso de las sesiones 06 a 11.
Python 3.11 o posterior; sin dependencias para el laboratorio local.
Versión: 1.1.0. Repositorio: https://github.com/focuz-ai/focuz-ai-engineering-rag

```powershell
python -m unittest discover -s tests -v
python -m rag
python -m rag.text2sql
python -m rag.estimation
```

La demo evalúa diez consultas sintéticas, nueve con relevantes y una sin respuesta.
Imprime evidencias y métricas; son pruebas de funcionamiento, no un benchmark de
calidad empresarial ni una evaluación de un LLM. Los vectores son conteos manuales
de cuatro grupos de palabras: NO son embeddings aprendidos ni búsqueda semántica
general. BM25 y RRF se implementan para hacer visible el cálculo.
El coseno rechaza dimensiones incompatibles y vectores vacíos. En esta demo un
vector nulo significa ausencia de conceptos y recibe puntuación cero; no se
interpreta como un coseno geométrico definido.

## Flujo

Identidad verificada en servidor → filtro tenant/roles/vigencia → BM25 y vector
didáctico → RRF → evidencia → respuesta extractiva con ID fuente.
La fecha final es exclusiva y la inicial inclusiva. Los documentos deben tener
IDs únicos por versión. Los metadatos de permiso nunca se aceptan del LLM.
La tarifa de A es 30 unidades hasta el 31 de diciembre de 2026 y 40 desde el
1 de enero de 2027. El `valid_to` exclusivo de la versión anterior coincide con
el `valid_from` inclusivo de la nueva: nunca deben competir ambas en el ranking.
Las consultas históricas siguen recuperando la versión aplicable a su fecha.

## Corrección 1.0.1

Se cerró la vigencia de `A-price-v1` en `2027-01-01` y se añadieron casos de
regresión antes, en y después de la transición. Las pruebas comprueban tanto la
única versión autorizada y vigente como la respuesta y su cita, incluida una
consulta histórica después de una consulta actual. Es la corrección de TECH-01
de la revisión adversarial; no modifica el algoritmo de ranking.

## Laboratorio

1. Añade diez documentos distractores y tres consultas sin respuesta.
2. Demuestra que un usuario support no recibe A-admin-v1.
3. Consulta antes y después del cambio de política y valida la cita.
4. Sustituye el vector didáctico por un modelo de embeddings, conservando la interfaz.
5. Lleva el índice a pgvector y mide recall del índice aproximado frente al exacto.
6. Añade un cross encoder; evalúa si mejora nDCG con un coste aceptable.
7. Añade generación con LLM solo después de aprobar recuperación y permisos.

## Qué falta para producción

No hay ingesta real, OCR, parser de PDF, base vectorial, RLS, autenticación de red,
modelo de embeddings, reranker ni generador LLM. Los filtros en memoria enseñan el
contrato de seguridad; no reemplazan RLS y políticas del servicio. Un documento con
solo una palabra coincidente puede ser irrelevante: el score no es una probabilidad.
Se necesita dataset independiente, threshold calibrado, citas por afirmación,
reindexado atómico, borrado y pruebas de fuga. La pregunta no modifica permisos.

## Demos del workshop (1.1.0)

### Consulta estructurada a datos

`rag.text2sql` crea cuatro proyectos ficticios en una SQLite temporal. Admite
dos preguntas: `listar proyectos activos` y `presupuesto total de proyectos activos`.
El planificador determinista produce `QueryPlan(intent, status='active', limit=10)`;
no es un traductor general ni llama un LLM. `execute_plan(path, principal, plan)`
acepta solo `list_projects/total_budget`, estados `active/closed` y límite entero
1–50. Requiere rol `analyst`; el tenant procede de identidad confiable.

La ejecución selecciona SQL fijo, enlaza parámetros, abre la base con `mode=ro`,
activa `query_only`, aplica authorizer y limita instrucciones mediante progress
handler. No existe una interfaz que ejecute SQL libre generado por un modelo.
La demo devuelve IDs 1 y 2 para A y total `200000` céntimos; el proyecto de B no
aparece. Una interrupción por presupuesto es un error, no una respuesta vacía.
La base real requeriría permisos propios de solo lectura y límites del servidor.

### Estimar con evidencia y abstenerse

`HistoricalEstimator.estimate(description, principal, on)` reutiliza el filtro
tenant/roles/vigencia de `Retriever`. Con al menos 50% de cobertura léxica de la
consulta, calcula la mediana de horas históricas y devuelve IDs de evidencia.
Este umbral es ilustrativo, no una probabilidad ni una validación de relevancia.
Sin precedentes admitidos devuelve `hours=None`, `evidence=[]`, `abstained=true`.
La ingesta valida horas positivas y finitas; `price` usa Decimal y redondeo
monetario explícito. Rechaza floats para evitar ambigüedad de representación.

Contrato numérico de 1.1.0: horas de cálculo entre 0 (excluido) y 100000, tarifa
entre 0 (excluido) y 1000000, contingencia entre 0 y 100 inclusive. Las tres
entradas admiten como máximo 64 posiciones decimales; el límite cuenta también
ceros finales de su representación. Se rechazan expresamente valores con mayor
escala mediante `ValueError`, sin truncarlos. Los históricos admiten 63 posiciones:
se reserva una para que la mediana exacta de dos valores siga siendo válida
como entrada monetaria. Es una restricción documentada añadida tras la revisión.

La mediana y el precio usan un contexto local de 256 cifras con configuración
propia de redondeo, exponentes y excepciones; no heredan la configuración Decimal
del consumidor. Con los rangos anteriores, los productos caben exactamente antes
del único redondeo final a céntimos mediante `ROUND_HALF_UP`.
Por ejemplo, una hora a `1.00499999999999999999999999999` resulta en `1.00`,
mientras que a `1.005` resulta en `1.01`. Las regresiones contrastan fracciones
exactas y un contexto global hostil con baja precisión y excepciones activadas.

La fixture de autenticación usa 8 y 12 horas autorizadas: mediana 10 y precio
`660.00` para tarifa 60 y contingencia 10%. Los antecedentes de otra empresa,
sin rol o vencidos no alteran el resultado. La tarea meteorológica se abstiene.

### Intercambio entre repositorios

Desde este repositorio crea un archivo nuevo:

```powershell
python -m rag.estimation --export intercambio.json
```

El contrato JSON versión 1 contiene `tenant`, `tasks`, `estimates` y la marca
`data_kind=synthetic_workshop_fixture`. Copia el archivo al laboratorio de agentes
y ejecuta `python -m agents.estimation --input intercambio.json`. La segunda
demo valida el ámbito y formato, atraviesa las dos aprobaciones ficticias y
completa manualmente una tarea sin precedente. Resultado esperado: 14 horas y
`924.00` EUR. Son etapas separadas de una práctica; el fichero no autentica
usuarios ni demuestra procedencia criptográfica de las citas.

### Cotejo de demos

| Fuente LIDR | Práctica Focuz | Alcance ejecutable |
| --- | --- | --- |
| Text2SQL (Python/LangChain/Chainlit) | `rag.text2sql` | Planificación finita y SQL autorizado en SQLite |
| Plataforma RAG (Rails) y servicio (FastAPI/pgvector) | `rag.estimation` | Recuperación local, mediana, citas, abstención y precio |
| Estimador de proyectos con revisión humana | JSON de intercambio y `agents.estimation` | Contrato entre etapas y dos gates locales |

Son implementaciones educativas originales. No se copia código LIDR ni se
presentan Rails, Chainlit, LangChain, embeddings aprendidos o pgvector como
integraciones ejecutadas. Para conectar un LLM, su salida debe transformarse
en un plan validado; las credenciales y el tenant permanecen fuera del prompt.

## Fuentes

https://github.com/pgvector/pgvector
https://qdrant.tech/documentation/concepts/hybrid-queries/
https://www.sbert.net/examples/cross_encoder/applications/README.html
https://www.postgresql.org/docs/current/ddl-rowsecurity.html
https://www.lidr.co/ai-engineering/ (secuencia curricular)

Consulta: 28 de octubre de 2026. Véase NOTICE.md.

Fuentes de las nuevas prácticas, consultadas el 2 de noviembre de 2026:

- https://lidr.notion.site/material-workshop-ai-engineer-pro
- https://github.com/LIDR-ai/lidr-text2sql-agent-demo
- https://github.com/LIDR-ai/lidr-rag-estimation-platform-demo
- https://github.com/LIDR-ai/lidr-rag-estimation-service-demo
- https://github.com/LIDR-ai/lidr-it-estimator-demo
- https://docs.python.org/3/library/sqlite3.html
