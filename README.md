# Retrieval híbrido con aislamiento y vigencia

Autor: [Focuz](https://www.focuz.io/). Caso de las sesiones 06 a 11.
Python 3.11 o posterior; sin dependencias para el laboratorio local.

```powershell
python -m unittest discover -s tests -v
python -m rag
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

## Fuentes

https://github.com/pgvector/pgvector
https://qdrant.tech/documentation/concepts/hybrid-queries/
https://www.sbert.net/examples/cross_encoder/applications/README.html
https://www.postgresql.org/docs/current/ddl-rowsecurity.html
https://www.lidr.co/ai-engineering/ (secuencia curricular)

Consulta: 28 de octubre de 2026. Véase NOTICE.md.
