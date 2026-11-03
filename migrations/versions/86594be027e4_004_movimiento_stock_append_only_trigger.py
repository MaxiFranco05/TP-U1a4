"""004_movimiento_stock_append_only_trigger

Revision ID: 86594be027e4
Revises: 13538b23627b
Create Date: 2026-11-03 14:18:57.641429

Revisión manual / Escrita a mano (Parcial Ej. 7, RN-12):
- Esta migración se escribe a mano (`alembic revision` sin `--autogenerate`) porque
  Alembic `--autogenerate` compara tablas, columnas, índices y restricciones declarativas
  en `SQLModel.metadata`, pero no detecta funciones PL/pgSQL (`CREATE FUNCTION`) ni
  disparadores (`CREATE TRIGGER`) del catálogo de PostgreSQL.
- En `upgrade()` instala la función `fn_movimiento_stock_append_only()` y el disparador
  `trg_movimiento_stock_append_only` (`BEFORE UPDATE OR DELETE ON movimiento_stock FOR EACH ROW`)
  que rechaza cualquier modificación o eliminación de filas existentes con código de error
  `integrity_constraint_violation` (RN-12, caso de prueba `C-14`).
- En `downgrade()` elimina el disparador y la función en orden inverso para mantener el
  ciclo `upgrade head` -> `downgrade base` -> `upgrade head` 100% reversible.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '86594be027e4'
down_revision: Union[str, Sequence[str], None] = '13538b23627b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Instala función PL/pgSQL y trigger appendOnly sobre movimiento_stock (RN-12)."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_movimiento_stock_append_only()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'La tabla movimiento_stock es de sólo agregado (RN-12): no se permite % sobre filas existentes.', TG_OP
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_movimiento_stock_append_only
        BEFORE UPDATE OR DELETE ON movimiento_stock
        FOR EACH ROW
        EXECUTE FUNCTION fn_movimiento_stock_append_only();
        """
    )


def downgrade() -> None:
    """Elimina el trigger appendOnly y la función PL/pgSQL de movimiento_stock."""
    op.execute("DROP TRIGGER IF EXISTS trg_movimiento_stock_append_only ON movimiento_stock;")
    op.execute("DROP FUNCTION IF EXISTS fn_movimiento_stock_append_only();")
