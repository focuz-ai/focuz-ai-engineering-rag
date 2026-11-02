import unittest
from datetime import date
from rag.core import Principal, Retriever, answer, recall_at_k, reciprocal_rank, cosine, Document, rrf, visible
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
    def test_price_transition_before_on_and_after_effective_date(self):
        for on, expected_id, price in [
            (date(2026,12,31),'A-price-v1','30'),
            (date(2027,1,1),'A-price-future','40'),
            (date(2027,1,2),'A-price-future','40'),
        ]:
            with self.subTest(on=on):
                # Metadata must leave exactly one applicable price, independently
                # of the ranking or the wording that favored the old policy.
                active = [d.id for d in DOCS if 'price' in d.id and visible(d,self.p,on)]
                self.assertEqual(active,[expected_id])
                result = answer('unidades mensuales',self.p,on,self.r)
                self.assertEqual(result['citations'],[expected_id])
                self.assertIn(price,result['text'])
                self.assertFalse(result['abstained'])
    def test_price_historical_query_after_current_query(self):
        current = answer('tarifa plan',self.p,date(2027,1,2),self.r)
        historical = answer('tarifa plan',self.p,date(2026,10,28),self.r)
        self.assertEqual(current['citations'],['A-price-future'])
        self.assertEqual(historical['citations'],['A-price-v1'])
        self.assertIn('30',historical['text'])
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
    def test_cosine_dimensions_and_known_value(self):
        for a,b in [([1],[1,10]),([1,10],[1]),([],[])]:
            with self.subTest(a=a,b=b), self.assertRaises(ValueError):
                cosine(a,b)
        self.assertAlmostEqual(cosine([1,0],[0.8,0.6]),0.8)
    def test_metric_k_validation(self):
        for k in [-1,0,1.5,True]:
            with self.subTest(metric='recall',k=k), self.assertRaises(ValueError):
                recall_at_k(['a'],['a'],k)
        for k in [-1,1.5,True]:
            with self.subTest(metric='rrf',k=k), self.assertRaises(ValueError):
                rrf([('a',1.0)],k=k)
        self.assertEqual(rrf([('a',1.0)],k=0),[('a',1.0)])
    def test_bad_ids(self):
        with self.assertRaises(ValueError): Retriever([DOCS[0],DOCS[0]])
    def test_empty_and_bad_limit(self):
        self.assertEqual(self.r.search('',self.p,self.on),[])
        for limit in [0,-1,1.5,True]:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                self.r.search('soporte',self.p,self.on,limit)

if __name__ == '__main__': unittest.main()
