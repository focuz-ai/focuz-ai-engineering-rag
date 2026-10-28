"""Retrieval didáctico stdlib. Los vectores por conceptos NO son embeddings aprendidos."""
from dataclasses import dataclass
from datetime import date
from math import log, sqrt
import re
import unicodedata

STOP = {'de','el','la','los','las','un','una','y','en','a','es','del','para','cual','como','se','que'}
def tokens(text):
    clean = ''.join(c for c in unicodedata.normalize('NFD',text.lower())
                    if unicodedata.category(c) != 'Mn')
    return [w for w in re.findall(r'\w+', clean) if w not in STOP]

@dataclass(frozen=True)
class Principal:
    tenant: str
    roles: tuple[str,...]

@dataclass(frozen=True)
class Document:
    id: str
    tenant: str
    text: str
    roles: tuple[str,...]
    valid_from: str
    valid_to: str | None = None

def visible(doc, principal, on):
    return (doc.tenant == principal.tenant
        and bool(set(doc.roles).intersection(principal.roles))
        and date.fromisoformat(doc.valid_from) <= on
        and (doc.valid_to is None or on < date.fromisoformat(doc.valid_to)))

def bm25(query, docs):
    terms = set(tokens(query))
    bags = [tokens(d.text) for d in docs]
    n = len(docs)
    avg = sum(map(len,bags))/n if n else 1
    result = []
    for doc, bag in zip(docs,bags):
        score = 0.0
        for term in terms:
            tf = bag.count(term)
            if not tf: continue
            df = sum(term in b for b in bags)
            idf = log(1 + (n-df+0.5)/(df+0.5))
            score += idf * tf * 2.2/(tf + 1.2*(0.25+0.75*len(bag)/max(avg,1)))
        if score > 0: result.append((doc.id, score))
    return sorted(result,key=lambda x:(-x[1],x[0]))

CONCEPTS = [set('horario horas apertura soporte'.split()),
            set('devolucion retorno reembolso dias'.split()),
            set('precio tarifa costo plan'.split()),
            set('token clave acceso seguridad'.split())]
def concept_vector(text):
    words = set(tokens(text))
    return [float(len(words & concept)) for concept in CONCEPTS]
def cosine(a,b):
    denominator = sqrt(sum(x*x for x in a)*sum(y*y for y in b))
    return sum(x*y for x,y in zip(a,b))/denominator if denominator else 0.0
def dense_demo(query, docs):
    q = concept_vector(query)
    scores = [(d.id,cosine(q,concept_vector(d.text))) for d in docs]
    return sorted((x for x in scores if x[1] > 0), key=lambda x:(-x[1],x[0]))
def rrf(*rankings, k=60):
    scores = {}
    for ranking in rankings:
        for rank, (doc_id, _) in enumerate(ranking,1):
            scores[doc_id] = scores.get(doc_id,0)+1/(k+rank)
    return sorted(scores.items(),key=lambda x:(-x[1],x[0]))

class Retriever:
    def __init__(self, docs):
        self.docs = list(docs)
        if len({d.id for d in self.docs}) != len(self.docs):
            raise ValueError('ID de documento duplicado')
    def search(self, query, principal, on, limit=3):
        if limit < 1: raise ValueError('limit debe ser positivo')
        if not tokens(query): return []
        # Filtrar antes del ranking y de calcular estadísticas del corpus.
        docs = [d for d in self.docs if visible(d,principal,on)]
        ranks = rrf(bm25(query,docs),dense_demo(query,docs))
        by_id = {d.id:d for d in docs}
        return [by_id[doc_id] for doc_id,_ in ranks[:limit]]

def answer(query, principal, on, retriever):
    evidence = retriever.search(query,principal,on,limit=1)
    if not evidence:
        return {'text':'No hay evidencia autorizada.','citations':[], 'abstained':True}
    # Extractivo. No redacta ni fusiona una respuesta generativa.
    doc = evidence[0]
    return {'text':doc.text, 'citations':[doc.id], 'abstained':False}

def recall_at_k(ranked, relevant, k):
    if not relevant: raise ValueError('Recall no definido sin relevantes')
    return len(set(ranked[:k]) & set(relevant))/len(set(relevant))
def reciprocal_rank(ranked, relevant):
    return next((1/i for i,x in enumerate(ranked,1) if x in relevant),0.0)
