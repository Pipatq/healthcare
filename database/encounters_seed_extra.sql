-- ============================================================================
-- Extra Encounter seed (apply on a RUNNING his_b_db without wiping volumes)
-- ============================================================================
--
-- Why this file exists:
--   his_b_init.sql only runs the FIRST TIME a fresh his_b_db volume is created.
--   If you've already started the stack, those new INSERTs won't show up unless
--   you wipe volumes (`docker compose down -v`). This file lets you seed the
--   same extra rows into a live database without losing existing data.
--
-- How to apply:
--
--   docker compose exec -T his_b_db psql -U postgres -d his_b \
--     < database/encounters_seed_extra.sql
--
--   (On Windows PowerShell:
--     Get-Content database/encounters_seed_extra.sql | `
--       docker compose exec -T his_b_db psql -U postgres -d his_b )
--
-- Idempotency:
--   Each row is guarded by a NOT EXISTS check on (patient_hn, period_start,
--   reason) so re-running is safe — duplicates won't be inserted.
-- ============================================================================

INSERT INTO encounters (patient_hn, status, class_code, class_display, period_start, period_end, reason)
SELECT v.patient_hn, v.status, v.class_code, v.class_display,
       v.period_start::timestamp, v.period_end::timestamp, v.reason
FROM (VALUES
    ('HN-0001', 'finished',    'AMB', 'outpatient encounter', '2025-12-01 15:00:00', '2025-12-01 16:00:00', 'Mental Disorder — initial assessment'),
    ('HN-0001', 'finished',    'AMB', 'outpatient encounter', '2026-02-14 13:30:00', '2026-02-14 14:15:00', 'Psychiatric follow-up — medication review'),
    ('HN-0002', 'finished',    'AMB', 'outpatient encounter', '2026-01-20 10:00:00', '2026-01-20 10:45:00', 'Anxiety disorder — counselling session'),
    ('HN-0003', 'finished',    'AMB', 'outpatient encounter', '2026-03-05 14:00:00', '2026-03-05 15:00:00', 'Depression screening (PHQ-9)'),
    ('HN-0004', 'finished',    'AMB', 'outpatient encounter', '2026-03-18 09:30:00', '2026-03-18 10:00:00', 'Insomnia consultation'),
    ('HN-0005', 'finished',    'EMER','emergency',            '2026-04-08 22:30:00', '2026-04-08 23:45:00', 'Acute panic attack'),
    ('HN-0002', 'in-progress', 'IMP', 'inpatient encounter',  '2026-04-23 08:00:00', NULL,                  'Mood disorder — observation admission'),
    ('HN-0004', 'planned',     'AMB', 'outpatient encounter', '2026-05-02 10:00:00', NULL,                  'Stress management — group therapy intake')
) AS v(patient_hn, status, class_code, class_display, period_start, period_end, reason)
WHERE NOT EXISTS (
    SELECT 1 FROM encounters e
    WHERE e.patient_hn   = v.patient_hn
      AND e.period_start = v.period_start::timestamp
      AND e.reason       = v.reason
);

-- Optional: verify what was inserted
-- SELECT id, patient_hn, status, class_code, period_start, reason
-- FROM encounters
-- ORDER BY period_start;
