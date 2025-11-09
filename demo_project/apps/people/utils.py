def get_user_name(user):
    """
    Return user's name formatted as "First Name L."

    Args:
        user: Django User object

    Returns:
        str: Formatted name like "Emma W." for "Emma Wilson"
    """
    if not user:
        return ""

    first_name = user.first_name.strip() if user.first_name else ""
    last_name = user.last_name.strip() if user.last_name else ""

    if first_name and last_name:
        return f"{first_name} {last_name[0]}."
    elif first_name:
        return first_name
    elif last_name:
        return last_name
    else:
        return user.username
