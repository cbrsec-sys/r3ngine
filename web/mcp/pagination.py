def parse_limit_offset(request, default=25, maximum=100):
    try:
        limit = int(request.query_params.get('limit', default))
    except (TypeError, ValueError):
        limit = default
    try:
        offset = int(request.query_params.get('offset', 0))
    except (TypeError, ValueError):
        offset = 0
    limit = max(1, min(limit, maximum))
    offset = max(0, offset)
    return limit, offset


def page_payload(items, total, limit, offset):
    count = len(items)
    has_more = offset + count < total
    return {
        'total_count': total,
        'count': count,
        'offset': offset,
        'limit': limit,
        'has_more': has_more,
        'next_offset': offset + count if has_more else None,
        'items': items,
    }


def page_queryset(qs, request, serializer):
    limit, offset = parse_limit_offset(request)
    total = qs.count()
    items = [serializer(obj) for obj in qs[offset:offset + limit]]
    return page_payload(items, total, limit, offset)
