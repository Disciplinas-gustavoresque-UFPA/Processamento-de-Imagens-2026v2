class Memento:
    def __init__(self, estado):
        self._estado = estado

    def obter_estado(self):
        return self._estado


class Historico:
    def __init__(self, limite=10):
        self._desfazer_pilha = []
        self._refazer_pilha = []
        self._limite = limite

    def salvar(self, estado):
        # Sempre que uma nova ação limpa a linha do tempo do Redo
        self._refazer_pilha.clear()
        self._desfazer_pilha.append(Memento(estado.copy()))

        if len(self._desfazer_pilha) > self._limite:
            self._desfazer_pilha.pop(0)

    def desfazer(self, estado_atual):
        if not self._desfazer_pilha:
            return None
        # Guarda o estado atual da tela na pilha de refazer
        self._refazer_pilha.append(Memento(estado_atual.copy()))
        return self._desfazer_pilha.pop().obter_estado()

    def refazer(self, estado_atual):
        if not self._refazer_pilha:
            return None
        # Devolve o estado atual da tela para a pilha de desfazer
        self._desfazer_pilha.append(Memento(estado_atual.copy()))
        return self._refazer_pilha.pop().obter_estado()