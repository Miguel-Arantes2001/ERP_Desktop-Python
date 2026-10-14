"""Repara referencias quebradas deixadas por produtos apagados antes de o
banco passar a validar chaves estrangeiras.

Os itens de venda viram itens genericos (product_id nulo + descricao), o que
preserva o valor da venda e o historico. Os movimentos de estoque orfaos sao
removidos: eles apontam para produto inexistente e ja nao aparecem em tela.

    python repair_orphans.py            # so mostra o que seria feito
    python repair_orphans.py --apply    # gera backup e aplica
"""

import argparse

from sqlalchemy import text

from backup import create_backup
from database import SessionLocal

ORPHAN_SALE_ITEMS = """
    SELECT id, sale_id, product_id, quantity, price
    FROM sale_items
    WHERE product_id IS NOT NULL
      AND product_id NOT IN (SELECT id FROM products)
    ORDER BY id
"""

ORPHAN_MOVEMENTS = """
    SELECT id, product_id, type, quantity, reason
    FROM stock_movements
    WHERE product_id NOT IN (SELECT id FROM products)
    ORDER BY id
"""


def repair(apply_changes: bool) -> None:
    db = SessionLocal()
    try:
        items = db.execute(text(ORPHAN_SALE_ITEMS)).fetchall()
        movements = db.execute(text(ORPHAN_MOVEMENTS)).fetchall()

        if not items and not movements:
            print("Nenhuma referencia quebrada encontrada.")
            return

        print(f"{len(items)} item(ns) de venda viram item generico:")
        for item in items:
            print(
                f"  item #{item.id} (venda #{item.sale_id}) "
                f"-> description='Produto removido (#{item.product_id})'"
            )

        print(f"\n{len(movements)} movimento(s) de estoque serao apagados:")
        for movement in movements:
            print(
                f"  movimento #{movement.id} | produto inexistente "
                f"{movement.product_id} | {movement.type} {movement.quantity} "
                f"| motivo={movement.reason!r}"
            )

        if not apply_changes:
            print("\nNada foi alterado. Rode com --apply para aplicar.")
            return

        create_backup(force=True)

        for item in items:
            db.execute(
                text(
                    "UPDATE sale_items "
                    "SET product_id = NULL, description = :description "
                    "WHERE id = :id"
                ),
                {
                    "description": f"Produto removido (#{item.product_id})",
                    "id": item.id,
                },
            )

        for movement in movements:
            db.execute(
                text("DELETE FROM stock_movements WHERE id = :id"),
                {"id": movement.id},
            )

        db.commit()
        print("\nAlteracoes aplicadas.")

        remaining = db.execute(text("PRAGMA foreign_key_check")).fetchall()
        print(f"foreign_key_check: {len(remaining)} violacao(oes) restante(s)")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Repara referencias quebradas de produtos apagados"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="aplica as mudancas (sem esta flag apenas simula)",
    )
    args = parser.parse_args()

    repair(apply_changes=args.apply)
