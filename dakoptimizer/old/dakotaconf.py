from multidict import MultiDict


class DakotaConf:
    def __init__(self):
        self.methods = []
        self.variables = []
        self.responses = []
        self.interfaces = []
        self.models = []

    def read_in():


    def write_in():



class DictAsClass:
    def __init__(self, dictionary):
        for key, value in dictionary.items():
            if isinstance(value, dict):
                # Convert nested dictionaries to DictAsClass instances
                value = DictAsClass(value)
            self.__setattr__(key, value)


def dict_as_class(dictionary):
    return DictAsClass(dictionary)


def class_as_dict(obj):
    if not hasattr(obj, "__dict__"):
        return obj
    result = MultiDict()
    for key, val in obj.__dict__.items():
        if isinstance(val, DictAsClass):
            # Recursively convert nested DictAsClass instances
            result[key] = class_as_dict(val)
        else:
            result[key] = val
    return result


# Example usage
data = MultiDict({
    "name": "Freddy",
    "age": 30,
    "address": {
        "street": "Downing St",
        "city": "London",
        "country": {"name": "United Kingdom", "code": "UK"},
    },
})

data.add("name", "Freddy")

obj = DictAsClass(data)

print(obj.name)  # Alice
print(obj.address.street)  # Downing St
print(obj.address.country.name)  # United Kingdom

obj.test = 5

print(class_as_dict(obj))
