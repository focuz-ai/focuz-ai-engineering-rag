from .core import Document

DOCS = [
 Document('A-hours-v1','A','El horario de soporte era de 08 a 16 horas.',('support',),'2025-01-01','2026-01-01'),
 Document('A-hours-v2','A','El horario de soporte es de 09 a 18 horas.',('support',),'2026-01-01'),
 Document('B-hours-v1','B','El horario de soporte es de 06 a 12 horas.',('support',),'2026-01-01'),
 Document('A-refund-v1','A','La devolución y reembolso se solicitan dentro de 7 días.',('support',),'2026-01-01'),
 Document('B-refund-v1','B','La devolución y reembolso se solicitan dentro de 15 días.',('support',),'2026-01-01'),
 Document('A-admin-v1','A','La clave de acceso ficticia administrativa es EJEMPLO-NO-SECRETO.',('admin',),'2026-01-01'),
 Document('A-price-v1','A','La tarifa del plan ficticio es 30 unidades mensuales.',('support',),'2026-01-01'),
 Document('A-price-future','A','La tarifa futura del plan ficticio será 40 unidades.',('support',),'2027-01-01'),
]

CASES = [
 {'id':'q1','tenant':'A','query':'horario de soporte','expected':['A-hours-v2'],'on':'2026-10-28'},
 {'id':'q2','tenant':'B','query':'horario de soporte','expected':['B-hours-v1'],'on':'2026-10-28'},
 {'id':'q3','tenant':'A','query':'devolucion reembolso','expected':['A-refund-v1'],'on':'2026-10-28'},
 {'id':'q4','tenant':'B','query':'devolucion reembolso','expected':['B-refund-v1'],'on':'2026-10-28'},
 {'id':'q5','tenant':'A','query':'tarifa plan','expected':['A-price-v1'],'on':'2026-10-28'},
 {'id':'q6','tenant':'A','query':'horario soporte','expected':['A-hours-v1'],'on':'2025-10-28'},
 {'id':'q7','tenant':'A','query':'volcan asteroide','expected':[],'on':'2026-10-28'},
]
