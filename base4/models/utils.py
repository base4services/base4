from tortoise.expressions import Q


def find_field_in_q(q_object, field_name):
    if isinstance(q_object, Q):
        # Check the current Q object's filters directly
        if not q_object.children:
            if field_name in q_object.filters:
                return {field_name: q_object.filters[field_name]}

        # Recursively check each child of the Q object
        for child in q_object.children:
            if isinstance(child, tuple):
                if child[0] == field_name:
                    return child[1]
            elif isinstance(child, Q):
                result = find_field_in_q(child, field_name)
                if result is not None:
                    return result

    return None
