import sys
import json

# ==============================================================================
# general io


def read_file(filename):
    with open(filename, "r") as f:
        return f.read()


def write_file(filename, string):
    with open(filename, "w") as f:
        f.write(string)


def to_jsonobj(jsonstr):
    return json.loads(jsonstr)


def to_jsonstr(jsonobj):
    return json.dumps(jsonobj, indent=4)


def read_wsv(filename=None):
    """
    Read whitespace separated values file as a list of lists.
    """
    slines = []
    if filename is None:
        for line in sys.stdin:
            slines.append(line.strip().split())
    else:
        with open(filename) as file:
            slines = [[w for w in line.strip().split()] for line in file]
    return slines


def write_wsv(slines, filename=None):
    """
    Write list of lists into whitespace separated values file.
    """
    if filename is None:
        sys.stdout.write(
            "\n".join(" ".join(map(str, line)) for line in slines)
        )
        sys.stdout.write("\n")
    else:
        file_content = "\n".join(" ".join(map(str, line)) for line in slines)
        print(file_content)
        with open(filename, "w") as f:
            f.write(file_content)


# ==============================================================================
# dakota io
