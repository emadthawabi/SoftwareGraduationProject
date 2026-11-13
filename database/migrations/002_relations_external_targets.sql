-- 002_relations_external_targets.sql
-- Some relations point to legislation outside the corpus (e.g. the law's
-- المادة 140 repeals قانون العمل رقم 21 لسنة 1960). Such rows have no
-- to_maqam_id; their target is described in `evidence`.

ALTER TABLE legislation_relations ALTER COLUMN to_maqam_id DROP NOT NULL;

ALTER TABLE legislation_relations
    ADD COLUMN from_article INTEGER;   -- the المادة whose text states the relation

ALTER TABLE legislation_relations
    ADD CONSTRAINT legislation_relations_target_chk
    CHECK (to_maqam_id IS NOT NULL OR evidence IS NOT NULL);
