class Memento:
    def __init__(self, estado):
        self._estado = estado

    def obter_estado(self):
        return self._estado


class Historico:
    def __init__(self, limite=10):
        self._estados = []
        self._limite = limite

    def salvar(self, estado):
        self._estados.append(Memento(estado.copy()))

        if len(self._estados) > self._limite:
            self._estados.pop(0)

    def desfazer(self):
        if not self._estados:
            return None
        return self._estados.pop().obter_estado()