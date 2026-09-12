def remap_generic_relations(
    model,
    *,
    source_content_type,
    target_content_type,
    object_id_map,
):
    updates = []
    for relation in model.objects.filter(content_type=source_content_type):
        target_object_id = object_id_map.get(relation.object_id)
        if target_object_id is None:
            continue
        relation.content_type = target_content_type
        relation.object_id = target_object_id
        updates.append(relation)

    if updates:
        model.objects.bulk_update(updates, ["content_type", "object_id"])

    return len(updates)
