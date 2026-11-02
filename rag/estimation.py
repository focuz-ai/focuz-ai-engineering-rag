"""Estimación didáctica por precedentes autorizados, con abstención y Decimal."""
from dataclasses import dataclass
import argparse
from datetime import date
from decimal import (Context, Decimal, DivisionByZero, InvalidOperation,
                     Overflow, ROUND_HALF_UP, localcontext)
import json
from pathlib import Path
from statistics import median
from .core import Document, Principal, Retriever, tokens


def money_context():
    # <=64 decimales por entrada y rangos monetarios acotados: el producto
    # exacto necesita <210 dígitos. No heredar precisión/traps del consumidor.
    return Context(prec=256, rounding=ROUND_HALF_UP, Emin=-1000, Emax=1000,
                   capitals=1, clamp=0, flags=[],
                   traps=[InvalidOperation, DivisionByZero, Overflow])


def positive_decimal(value, maximum='1000000', max_decimal_places=64):
    if type(value) not in (str, int, Decimal):
        raise ValueError('Se requiere un decimal textual o entero, no float/bool')
    try:
        result = Decimal(value)
        if not result.is_finite() or not 0 < result <= Decimal(maximum):
            raise ValueError('Decimal fuera de rango')
        if max(-result.as_tuple().exponent, 0) > max_decimal_places:
            raise ValueError(f'Se permiten como máximo {max_decimal_places} decimales')
        return result
    except InvalidOperation:
        raise ValueError('Decimal inválido') from None


@dataclass(frozen=True)
class HistoricalTask:
    document: Document
    hours: str


class HistoricalEstimator:
    def __init__(self, tasks):
        self.tasks = list(tasks)
        self.retriever = Retriever(item.document for item in self.tasks)
        # Una mediana par puede añadir un decimal: reservar esa cifra permite
        # que su salida exacta siga cumpliendo el contrato monetario de 64.
        self.hours = {item.document.id: positive_decimal(item.hours, '100000', 63) for item in self.tasks}

    def estimate(self, description, principal, on, limit=3):
        words = set(tokens(description))
        if not words:
            return {'hours': None, 'evidence': [], 'abstained': True, 'method': 'authorized_median'}
        found = self.retriever.search(description, principal, on, limit=limit)
        # Umbral ilustrativo de cobertura léxica: no es confianza del modelo.
        evidence = [d for d in found if len(words & set(tokens(d.text))) / len(words) >= 0.5]
        with localcontext(money_context()):
            hours = median(self.hours[d.id] for d in evidence) if evidence else None
        return {'hours': str(hours) if hours is not None else None,
                'evidence': [d.id for d in evidence], 'abstained': hours is None,
                'method': 'authorized_median'}


def price(hours, hourly_rate, contingency_percent='0'):
    hours = positive_decimal(hours, '100000')
    rate = positive_decimal(hourly_rate)
    # Decimal exige también 0 <= contingencia <= 100 y rechaza NaN/infinito.
    if type(contingency_percent) not in (str, int, Decimal):
        raise ValueError('Contingencia inválida')
    try:
        contingency = Decimal(contingency_percent)
        if not contingency.is_finite() or not 0 <= contingency <= 100:
            raise ValueError('Contingencia fuera de rango')
        if max(-contingency.as_tuple().exponent, 0) > 64:
            raise ValueError('Se permiten como máximo 64 decimales')
    except InvalidOperation:
        raise ValueError('Contingencia inválida') from None
    with localcontext(money_context()):
        amount = hours * rate * (1 + contingency / 100)
        return str(amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def fixture():
    return [HistoricalTask(Document('A-auth-1', 'A', 'Autenticación login usuarios', ('analyst',), '2026-01-01'), '8'),
            HistoricalTask(Document('A-auth-2', 'A', 'Autenticación login usuarios', ('analyst',), '2026-01-01'), '12'),
            HistoricalTask(Document('B-auth-1', 'B', 'Autenticación login usuarios', ('analyst',), '2026-01-01'), '200'),
            HistoricalTask(Document('A-auth-expired', 'A', 'Autenticación login usuarios', ('analyst',), '2025-01-01', '2026-01-01'), '100')]


def workshop_exchange():
    """Contrato de intercambio ficticio para el segundo laboratorio de agentes."""
    tasks = [{'id': 'auth', 'description': 'Autenticación login usuarios'},
             {'id': 'novel', 'description': 'Adaptador sin precedente'}]
    estimator = HistoricalEstimator(fixture())
    estimates = []
    for task in tasks:
        result = estimator.estimate(task['description'], Principal('A', ('analyst',)), date(2026, 11, 2))
        estimates.append({'id': task['id'], 'hours': result['hours'], 'evidence': result['evidence']})
    return {'schema_version': 1, 'tenant': 'A', 'tasks': tasks, 'estimates': estimates,
            'data_kind': 'synthetic_workshop_fixture'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, help='Crear JSON de intercambio nuevo; no sobrescribe')
    args = parser.parse_args()
    if args.export:
        with args.export.open('x', encoding='utf-8') as stream:
            json.dump(workshop_exchange(), stream, ensure_ascii=False, indent=2)
        print(json.dumps({'exported': str(args.export), 'schema_version': 1}))
        return
    estimator = HistoricalEstimator(fixture())
    principal = Principal('A', ('analyst',))
    for description in ('Autenticación login usuarios', 'Simulación meteorológica'):
        result = estimator.estimate(description, principal, date(2026, 11, 2))
        result['price'] = price(result['hours'], '60', '10') if result['hours'] else None
        print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
