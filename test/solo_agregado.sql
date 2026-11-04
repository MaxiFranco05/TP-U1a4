-- ============================================================================
-- Caso C-14: Demostración de restricción de sólo-agregado (RN-12)
-- Disparador trg_movimiento_stock_solo_agregado instalado en la Migración 004.
-- Cualquier UPDATE o DELETE debe ser rechazado por PostgreSQL con error.
-- ============================================================================

\echo '--- Intentando UPDATE sobre movimiento_stock (debe fallar) ---'
UPDATE movimiento_stock
SET cantidad = 999
WHERE id = 1;

\echo '--- Intentando DELETE sobre movimiento_stock (debe fallar) ---'
DELETE FROM movimiento_stock
WHERE id = 1;
