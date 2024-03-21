def singleton(cls):
    instance = cls()

    def _return_instance(*args, **kwargs):
        return instance
    cls.__new__ = _return_instance

    return cls


@singleton
class Undefined(object):
    def __bool__(self):
        return False
