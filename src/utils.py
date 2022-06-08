class DDict(dict):
    def __getattr__(self, key):
        try:
            if isinstance(self[key], dict):
                self[key] = DDict(self[key])
            return self[key]
        except:
            print(self)
            raise ValueError(f"bad key: {key}")

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            value = DDict(value)
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as k:
            raise AttributeError(k)

    def __repr__(self):
        return '<DictX ' + dict.__repr__(self) + '>'