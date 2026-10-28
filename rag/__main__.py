from datetime import date
import json
from .core import Principal, Retriever, answer, recall_at_k, reciprocal_rank
from .data import DOCS, CASES

r = Retriever(DOCS)
recalls, rr, abstention = [], [], []
for c in CASES:
    p = Principal(c['tenant'],('support',))
    ranked = [d.id for d in r.search(c['query'],p,date.fromisoformat(c['on']))]
    result = answer(c['query'],p,date.fromisoformat(c['on']),r)
    if c['expected']:
        recalls.append(recall_at_k(ranked,c['expected'],3))
        rr.append(reciprocal_rank(ranked,c['expected']))
    else:
        abstention.append(result['abstained'])
    print(json.dumps({'case':c['id'],'ranked':ranked,'result':result},ensure_ascii=False))
print(json.dumps({'retrieval_cases':len(recalls),'recall_at_3':sum(recalls)/len(recalls),
 'mrr':sum(rr)/len(rr),'unanswerable_cases':len(abstention),
 'correct_abstentions':sum(abstention)},ensure_ascii=False))
