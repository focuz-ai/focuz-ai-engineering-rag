"""Lenguaje natural acotado -> plan tipado -> SQL parametrizado y solo lectura.

No ejecuta SQL del modelo. Los dos intents ilustran una frontera para integrar
un clasificador externo, no un traductor general de preguntas a SQL.
"""
from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from .core import Principal


@dataclass(frozen=True)
class QueryPlan:
    intent: str
    status: str = 'active'
    limit: int = 10


def plan_question(question):
    if not isinstance(question, str):
        raise ValueError('Pregunta inválida')
    questions = {'listar proyectos activos': 'list_projects',
                 'presupuesto total de proyectos activos': 'total_budget'}
    intent = questions.get(question.strip().casefold())
    if intent is None:
        raise ValueError('Pregunta fuera del catálogo; reformula o solicita revisión')
    return QueryPlan(intent)


def create_fixture(path):
    """Crea solo un archivo nuevo; no sobrescribe una base existente."""
    path = Path(path)
    with path.open('xb'):
        pass
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE projects(id INTEGER PRIMARY KEY, tenant TEXT, name TEXT, status TEXT, budget_cents INTEGER)')
        db.executemany('INSERT INTO projects VALUES (?,?,?,?,?)', [
            (1, 'A', 'Portal de soporte', 'active', 120000),
            (2, 'A', 'Integración de facturas', 'active', 80000),
            (3, 'A', 'Archivo histórico', 'closed', 25000),
            (4, 'B', 'Proyecto reservado', 'active', 999999)])
    db.close()


def execute_plan(path, principal, plan):
    """El servidor aporta Principal; no se toma tenant/roles del plan ni del LLM."""
    if 'analyst' not in principal.roles or not principal.tenant:
        raise PermissionError('Se requiere identidad de analista')
    if type(plan) is not QueryPlan or plan.intent not in ('list_projects', 'total_budget'):
        raise ValueError('Plan fuera del catálogo')
    if plan.status not in ('active', 'closed') or type(plan.limit) is not int or not 1 <= plan.limit <= 50:
        raise ValueError('Estado o límite inválido')
    queries = {
        'list_projects': 'SELECT id, name, budget_cents FROM projects WHERE tenant=? AND status=? ORDER BY id LIMIT ?',
        'total_budget': 'SELECT COALESCE(SUM(budget_cents),0) AS total_cents FROM projects WHERE tenant=? AND status=?'}
    sql = queries[plan.intent]
    params = (principal.tenant, plan.status)
    if plan.intent == 'list_projects':
        params += (plan.limit,)
    # mode=ro impide crear la BD por error; query_only es otra defensa local.
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    db = sqlite3.connect(uri, uri=True)
    try:
        db.execute('PRAGMA query_only=ON')
        def authorize(operation, table, column, database, trigger):
            if operation == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if operation == sqlite3.SQLITE_READ and table == 'projects' and database == 'main':
                return sqlite3.SQLITE_OK
            if operation == sqlite3.SQLITE_FUNCTION and column in ('sum', 'coalesce'):
                return sqlite3.SQLITE_OK
            return sqlite3.SQLITE_DENY
        db.set_authorizer(authorize)
        # Cota adicional al coste de la consulta; una interrupción no es un resultado vacío.
        callbacks = 0
        def budget_exhausted():
            nonlocal callbacks
            callbacks += 1
            return callbacks > 100
        db.set_progress_handler(budget_exhausted, 1000)
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute(sql, params)]
        return {'intent': plan.intent, 'sql_template': sql, 'rows': rows,
                'scope': principal.tenant, 'simulated_planner': True}
    finally:
        db.close()


def main():
    with TemporaryDirectory() as temp:
        path = Path(temp) / 'fixture.sqlite3'
        create_fixture(path)
        principal = Principal('A', ('analyst',))
        for question in ('listar proyectos activos', 'presupuesto total de proyectos activos'):
            print(json.dumps(execute_plan(path, principal, plan_question(question)), ensure_ascii=False))


if __name__ == '__main__':
    main()
