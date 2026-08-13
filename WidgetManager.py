class WidgetManager:
    """Tracks which widget is currently active for display."""

    def __init__(self, names):
        if not names:
            raise ValueError("WidgetManager needs at least one widget name")
        self._names = list(names)
        self._index = 0

    @property
    def current(self):
        return self._names[self._index]

    @property
    def names(self):
        return list(self._names)

    def select(self, name_or_index):
        if isinstance(name_or_index, int):
            self._index = name_or_index % len(self._names)
        else:
            self._index = self._names.index(name_or_index)
        return self.current

    def next(self):
        self._index = (self._index + 1) % len(self._names)
        return self.current

    def prev(self):
        self._index = (self._index - 1) % len(self._names)
        return self.current
