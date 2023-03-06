# 2022-11-14 09:13 How many open datasets there are

psql -h localhost -U adp adp-dev

SELECT
  EXTRACT(YEAR FROM d.created) AS year,
  count(*) as datasets
FROM "dataset" d
LEFT JOIN (
  SELECT
    dataset_id,
    COUNT(dataset_id) AS dist_count
  FROM "dataset_distribution"
  GROUP BY dataset_id
) r ON r.dataset_id = d.id
LEFT JOIN "organization" o ON o.id = d.organization_id
WHERE r.dist_count > 0
  AND d.is_public
  AND d.deleted IS NULL
  AND o.deleted IS NULL
GROUP BY EXTRACT(YEAR FROM d.created)
ORDER BY EXTRACT(YEAR FROM d.created)
;


SELECT
  count(*) as datasets
FROM "dataset" d
LEFT JOIN (
  SELECT
    dataset_id,
    COUNT(dataset_id) AS dist_count
  FROM "dataset_distribution"
  GROUP BY dataset_id
) r ON r.dataset_id = d.id
LEFT JOIN "organization" o ON o.id = d.organization_id
WHERE r.dist_count > 0
  AND d.is_public
  AND d.deleted IS NULL
  AND o.deleted IS NULL
  AND d.created > '2021-01-01'
;


SELECT
  count(*) as datasets
FROM "dataset" d
LEFT JOIN (
  SELECT
    dataset_id,
    COUNT(dataset_id) AS dist_count
  FROM "dataset_distribution"
  GROUP BY dataset_id
) r ON r.dataset_id = d.id
LEFT JOIN "organization" o ON o.id = d.organization_id
WHERE d.is_public
  AND d.deleted IS NULL
  AND o.deleted IS NULL
  AND d.created > '2021-01-01'
;


SELECT
  count(*) as datasets
FROM "dataset" d
LEFT JOIN (
  SELECT
    dataset_id,
    COUNT(dataset_id) AS dist_count
  FROM "dataset_distribution"
  GROUP BY dataset_id
) r ON r.dataset_id = d.id
LEFT JOIN "organization" o ON o.id = d.organization_id
WHERE d.is_public
  AND r.dist_count > 0
  AND d.deleted IS NULL
  AND o.deleted IS NULL
;

\q
