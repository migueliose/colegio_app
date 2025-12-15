# colegio_app/routers.py
class AntiguaDBRouter:
    """
    Router para manejar la base de datos antigua
    """
    def db_for_read(self, model, **hints):
        if model._meta.app_label == 'antigua_bd':
            return 'antigua'
        return None

    def db_for_write(self, model, **hints):
        # Solo lectura para la BD antigua
        if model._meta.app_label == 'antigua_bd':
            return 'antigua'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        # Permitir relaciones entre objetos de la misma BD
        if obj1._meta.app_label == 'antigua_bd' and obj2._meta.app_label == 'antigua_bd':
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label == 'antigua_bd':
            return db == 'antigua'
        return db == 'default'