from django.db import migrations


REVERSE_SQL = """
CREATE OR REPLACE VIEW dsa_model_dependencies AS
WITH RECURSIVE dependencies AS (
SELECT
    mod.id root_id,
    mod.metadata_version_id root_version_id,
    mod.dataset_id root_dataset_id,
    mod.id current_id,
    ARRAY[mod.id]::bigint[] path,
    0 depth
FROM model mod
UNION ALL
SELECT
    dep.root_id root_id,
    dep.root_version_id root_version_id,
    dep.root_dataset_id root_dataset_id,
    prp.ref_model_id current_id,
    dep.path || prp.ref_model_id path,
    dep.depth + 1 depth
FROM dependencies dep
JOIN model cur
    ON cur.id = dep.current_id
JOIN django_content_type model_ct
    ON model_ct.app_label = 'vitrina_structure'
    AND model_ct.model = 'model'
JOIN django_content_type prop_ct
    ON prop_ct.app_label = 'vitrina_structure'
    AND prop_ct.model = 'property'
JOIN metadata cur_meta
    ON cur_meta.content_type_id = model_ct.id
    AND cur_meta.object_id = cur.id
    AND cur_meta.metadata_version_id = cur.metadata_version_id
JOIN property prp
    ON prp.model_id = dep.current_id
JOIN metadata prop_meta
    ON prop_meta.content_type_id = prop_ct.id
    AND prop_meta.object_id = prp.id
    AND prop_meta.metadata_version_id = prp.metadata_version_id
WHERE
    dep.depth < 20
    AND prp.given IS TRUE
    AND prp.ref_model_id IS NOT NULL
    AND NOT prp.ref_model_id = ANY(dep.path)
    AND (
        cur.dataset_id = dep.root_dataset_id
        OR (
            cur.dataset_id != dep.root_dataset_id
            AND cur_meta.ref IS NOT NULL
            AND prop_meta.name = ANY(
                string_to_array(regexp_replace(cur_meta.ref, '\s+', '', 'g'), ',')
            )
        )
    )
)
SELECT DISTINCT
dep.root_id root_model_id,
dep.root_version_id root_version_id,
dep.current_id child_model_id,
array_to_string(dep.path, '->') path,
dep.depth,
dep.root_dataset_id root_dataset_id
FROM
dependencies dep
JOIN model mod ON mod.id = dep.current_id
WHERE
dep.depth > 0
AND mod.dataset_id != dep.root_dataset_id
ORDER BY
    dep.root_id, dep.depth DESC, dep.current_id;
"""


FORWARD_SQL = """
CREATE OR REPLACE VIEW dsa_model_dependencies AS
WITH RECURSIVE dependencies AS (
SELECT
    mod.id root_id,
    mod.metadata_version_id root_version_id,
    mod.dataset_id root_dataset_id,
    mod.id current_id,
    ARRAY[mod.id]::bigint[] path,
    0 depth
FROM model mod
UNION ALL
SELECT
    dep.root_id root_id,
    dep.root_version_id root_version_id,
    dep.root_dataset_id root_dataset_id,
    next_step.next_id current_id,
    dep.path || next_step.next_id path,
    dep.depth + 1 depth
FROM dependencies dep
JOIN model cur
    ON cur.id = dep.current_id
CROSS JOIN LATERAL (
    SELECT prp.ref_model_id AS next_id
    FROM property prp
    JOIN django_content_type model_ct
        ON model_ct.app_label = 'vitrina_structure'
        AND model_ct.model = 'model'
    JOIN django_content_type prop_ct
        ON prop_ct.app_label = 'vitrina_structure'
        AND prop_ct.model = 'property'
    JOIN metadata cur_meta
        ON cur_meta.content_type_id = model_ct.id
        AND cur_meta.object_id = cur.id
        AND cur_meta.metadata_version_id = cur.metadata_version_id
    JOIN metadata prop_meta
        ON prop_meta.content_type_id = prop_ct.id
        AND prop_meta.object_id = prp.id
        AND prop_meta.metadata_version_id = prp.metadata_version_id
    WHERE prp.model_id = cur.id
        AND prp.given IS TRUE
        AND prp.ref_model_id IS NOT NULL
        AND (
            cur.dataset_id = dep.root_dataset_id
            OR (
                cur.dataset_id != dep.root_dataset_id
                AND cur_meta.ref IS NOT NULL
                AND prop_meta.name = ANY(
                    string_to_array(regexp_replace(cur_meta.ref, '\\s+', '', 'g'), ',')
                )
            )
        )
    UNION ALL
    SELECT b.model_id AS next_id
    FROM base b
    WHERE b.id = cur.base_id
        AND b.model_id IS NOT NULL
) AS next_step
WHERE
    dep.depth < 20
    AND NOT next_step.next_id = ANY(dep.path)
)
SELECT DISTINCT
dep.root_id root_model_id,
dep.root_version_id root_version_id,
dep.current_id child_model_id,
array_to_string(dep.path, '->') path,
dep.depth,
dep.root_dataset_id root_dataset_id
FROM
dependencies dep
JOIN model mod ON mod.id = dep.current_id
WHERE
dep.depth > 0
AND mod.dataset_id != dep.root_dataset_id
ORDER BY
    dep.root_id, dep.depth DESC, dep.current_id;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("vitrina_structure", "0017_umldiagram"),
    ]

    operations = [
        migrations.RunSQL(
            sql=FORWARD_SQL,
            reverse_sql=REVERSE_SQL,
        ),
    ]
