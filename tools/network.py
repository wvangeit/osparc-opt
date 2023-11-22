import os


def get_osparc_hostname(type):
    known_types = ["map", "optimizer", "evaluator1", "evaluator2"]

    if type not in known_types:
        raise ValueError(
            f"Received unknown type for get_osparc_hostname: {type}"
        )

    var_name = f"OSPARC_{type.upper()}_HOSTNAME"

    return os.environ[var_name] if var_name in os.environ else type
