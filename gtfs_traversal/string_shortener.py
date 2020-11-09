class StringShortener:
    def __init__(self):
        self._shorten_dict = dict()
        self._lengthen_dict = dict()

    def shorten(self, string):
        if string not in self._shorten_dict:
            new_id = str(len(self._shorten_dict))
            self._shorten_dict[string] = new_id
            self._lengthen_dict[new_id] = string

        return self._shorten_dict[string]

    def lengthen(self, string):
        return self._lengthen_dict[string]
