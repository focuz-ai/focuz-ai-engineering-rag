import unittest
from datetime import date
from rag.core import Principal, Retriever, answer, recall_at_k, reciprocal_rank, cosine, Document
from rag.data import DOCS, CASES

class RAGTests(unittest.TestCase):
    def setUp(self):
        self.r = Retriever(DOCS)
        self.p = Principal('A',('support',))
        self.on = date(2026,10,28)
    def test_dataset_top_result(self):
        for c in CASES:
            with self.subTest(case=c['id']):
                ranked = self.r.search(c['query'],Principal(c['tenant'],('support',)),date.fromisoformat(c['on']))
                self.assertEqual([x.id for x in ranked[:1]],c['expected'])
    def test_no_cross_tenant(self):
        self.assertTrue(all(d.tenant=='A' for d in self.r.search('soporte reembolso plan',self.p,self.on)))
    def test_hidden_admin(self):
        self.assertEqual(self.r.search('clave acceso',self.p,self.on),[])
    def test_role_change_retrieval(self):
        self.assertEqual(self.r.search('clave acceso',Principal('A',('admin',)),self.on)[0].id,'A-admin-v1')
    def test_validity_exclusive_end(self):
        ranked = self.r.search('horario soporte',self.p,date(2026,1,1))
        self.assertEqual(ranked[0].id,'A-hours-v2')
    def test_future_excluded(self):
        self.assertEqual(self.r.search('tarifa plan',self.p,self.on)[0].id,'A-price-v1')
    def test_unknown_abstains(self):
        self.assertTrue(answer('asteroide volcan',self.p,self.on,self.r)['abstained'])
    def test_evidence_exact(self):
        result = answer('horario soporte',self.p,self.on,self.r)
        doc = next(x for x in DOCS if x.id==result['citations'][0])
        self.assertEqual(result['text'],doc.text)
    def test_metrics(self):
        self.assertEqual(recall_at_k(['a','b'],['b','c'],2),0.5)
        self.assertEqual(reciprocal_rank(['a','b'],['b']),0.5)
    def test_zero_cosine(self):
        self.assertEqual(cosine([0,0],[1,0]),0)
    def test_bad_ids(self):
        with self.assertRaises(ValueError): Retriever([DOCS[0],DOCS[0]])
    def test_empty_and_bad_limit(self):
        self.assertEqual(self.r.search('',self.p,self.on),[])
        with self.assertRaises(ValueError): self.r.search('soporte',self.p,self.on,0)

if __name__ == '__main__': unittest.main()
