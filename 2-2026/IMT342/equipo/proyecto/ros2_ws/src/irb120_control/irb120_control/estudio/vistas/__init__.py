"""Vistas (una por pestaña) del Estudio."""


class Vista:
    """Contrato común: `frame` y ganchos que la App llama; todos opcionales."""
    titulo = ''

    def actualizar(self, estado, error):
        pass

    def al_cambiar(self, evento):
        """evento: 'plan' | 'lista' | 'tema'."""
