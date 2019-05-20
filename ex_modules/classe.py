# coding=utf-8
from numpy import mean, var, unique


class Classe:
    def __init__(self, valores=None, nome=None):
        self._name = nome
        self.raster_path = None
        if valores:
            self._values = valores
            self._media = mean(valores)
            self._variancia = var(valores)
        else:
            self._values = []
            self._media = 0
            self._variancia = 0

    # Funções essenciais
    def sum_sqr_dev(self):
        if self._media and self._values:
            _sum = 0
            for value in self._values:
                _sum += (value - self._media)**2
            return _sum
        return 0

    # Métodos de alteração de valores
    def add_value(self, value):
        self._values.append(value)
        self.att_params()

    def remove_value(self, value):
        self._values.remove(value)
        self.att_params()

    def add_raster_path(self, path):
        self.raster_path = path

    # Métodos de atualização de valoress
    def att_params(self):
        self._values = sorted(self._values)
        self._media = mean(self._values)
        self._variancia = var(self._values)

    # Métodos GET
    def count_values(self):
        return len(self._values)

    def get_values(self):
        return self._values

    def get_variance(self):
        return self._variancia

    def get_name(self):
        return self._name

    def get_media(self):
        return self._media

    def get_unique_values(self):
        return unique(self._values)

    def max_sqr_dev(self):
        valor_max = 0
        value_max = 0
        for value in self._values:
            if valor_max < (value - self._media)**2:
                valor_max = (value - self._media)**2
                value_max = value
        return value_max

    # Método para exibição em console
    def __str__(self):
        text  = 'Classe: %s\n' % str(self._name)
        text += 'Total de pixels: %d\n' % self.count_values()

        if self._media:
            text += 'Média: %.5f\n' % self._media
        else:
            text += 'Média: Sem Valor\n'

        if self._variancia:
            text += 'Variância: %.5f\n' % self._variancia
        else:
            text += 'Variância: Sem Valor\n'

        return text