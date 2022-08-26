from urllib.parse import urlencode


def get_selected_value(request, title, multiple=False, is_int=True):
    selected_value = [] if multiple else None
    value = request.GET.getlist(title) if multiple else request.GET.get(title)
    if value:
        selected_value = value
        if is_int:
            try:
                selected_value = [int(val) for val in value] if multiple else int(value)
            except ValueError:
                return [] if multiple else None
    return selected_value


def get_filter_url(request, key, value, append=False):
    query_dict = dict(request.GET.copy())
    if append and key in query_dict:
        query_dict[key].append(value)
    else:
        query_dict[key] = [value]
    return "?" + urlencode(query_dict, True)
