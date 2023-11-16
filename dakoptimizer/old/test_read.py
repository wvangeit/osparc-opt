def read_dakota_config(file_path):
    def get_indent_level(line):
        return len(line) - len(line.lstrip())

    config = {}
    context_stack = [config]
    last_indent_level = 0

    with open(file_path, "r") as file:
        for line in file:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue  # Skip empty lines and comments

            indent_level = get_indent_level(line)
            line = line.strip()

            # Adjust the context based on indentation level
            while indent_level > last_indent_level and len(context_stack) > 1:
                context_stack.pop()
                last_indent_level -= 1

            context_stack[-1][line] = {}
            context_stack.append(context_stack[-1][line])

            last_indent_level = indent_level

    return config


def read_dakota_config2(file_path):
    def get_indent_level(line):
        return len(line) - len(line.lstrip())

    config = {}

    context_stack = [(0, None, config)]

    with open(file_path, "r") as file:
        for line in file:
            line = line.rstrip()
            if not line or line.startswith("#"):
                continue  # Skip empty lines and comments

            indent_level = get_indent_level(line)
            line = line.strip()

            parent_indent_level, _, _ = context_stack[-1]

            # Adjust the context based on indentation level
            while (
                indent_level <= parent_indent_level and len(context_stack) > 1
            ):
                parent_indent_level, _, _ = context_stack.pop()
            # Detect key-value pairs or new sections
            if "=" in line:
                key, value = [
                    item.strip().strip('"') for item in line.split("=", 1)
                ]
                context_stack[-1][1][key] = value
            else:
                new_section = {}
                parent_indent_level, parent_name, parent_dict = context_stack[
                    -1
                ]
                print(indent_level, parent_indent_level, parent_name, line)

                if parent_name is None or indent_level > parent_indent_level:
                    # New top-level section or deeper indent
                    if line not in parent_dict:
                        parent_dict[line] = []
                    parent_dict[line].append(new_section)
                    context_stack.append((indent_level, line, new_section))
                else:
                    # Same level, but different section
                    config[line] = [new_section]
                    context_stack.append((indent_level, line, new_section))

    return config


def write_dakota_config(config, file_path):
    def write_section(file, section, content, indent=0):
        space = " " * indent
        if isinstance(content, list):
            for item in content:
                file.write(f"{space}{section}\n")
                write_section(file, section, item, indent + 2)
        elif isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, dict) or isinstance(value, list):
                    file.write(f"{space}{key}\n")
                    write_section(file, key, value, indent + 2)
                else:
                    file.write(f"{space}{key} = {value}\n")

    with open(file_path, "w") as file:
        for top_level_section, content in config.items():
            write_section(file, top_level_section, content)


def write_dakota_config2(config, file_path):
    def write_section(file, section, content, indent=0):
        space = " " * indent
        if isinstance(content, list):
            for item in content:
                # Write list items without repeating the section header
                write_section(file, None, item, indent)
        elif isinstance(content, dict):
            if section is not None:
                file.write(f"{space}{section}\n")
            for key, value in content.items():
                if isinstance(value, dict) or isinstance(value, list):
                    # Increase indent for nested sections
                    new_indent = indent + 4 if section is not None else indent
                    write_section(file, key, value, new_indent)
                else:
                    file.write(f"{space}{key} = {value}\n")

    with open(file_path, "w") as file:
        for top_level_section, content in config.items():
            write_section(file, top_level_section, content)


def write_dakota_config3(config, file_path):
    def write_section(file, content, indent=0):
        space = " " * indent
        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, dict):
                    # Write the section header and its content
                    file.write(f"{space}{key}\n")
                    write_section(file, value, indent + 4)
                elif isinstance(value, list):
                    # Handle lists of dictionaries
                    for item in value:
                        if isinstance(item, dict):
                            file.write(f"{space}{key}\n")
                            write_section(file, item, indent + 4)
                        else:
                            file.write(f"{space}{key} = {item}\n")
                else:
                    # Write key-value pairs
                    file.write(f"{space}{key} = {value}\n")

    with open(file_path, "w") as file:
        write_section(file, config)


import json

conf = read_dakota_config2("opt.in")
print(json.dumps(conf, indent=4))
write_dakota_config3(conf, "opt.out")
