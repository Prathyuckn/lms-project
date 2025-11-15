def convert_string_to_array(comma_string):
    if comma_string is None or "":
        return []

    if "," in comma_string:
        converted_array = comma_string.split(",")
        # Strip whitespace from each element
        converted_array = [item.strip() for item in converted_array]
        return converted_array
    else:
        return [comma_string]
