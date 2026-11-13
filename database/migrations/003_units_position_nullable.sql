-- 003_units_position_nullable.sql
-- Preambles and most annexes have no "order" in the source. Leave position
-- NULL for them instead of inventing one; display order is derived from
-- kind (preamble first) and after_article for annexes.

ALTER TABLE units ALTER COLUMN position DROP NOT NULL;
