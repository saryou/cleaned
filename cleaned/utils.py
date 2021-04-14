def singleton(cls):
    instance = cls()

    def _return_instance(*args, **kwargs):
        return instance
    cls.__new__ = _return_instance

    return cls


@singleton
class Undefined(object):
    """未定義であることを表現する"""

    def __bool__(self):
        return False
