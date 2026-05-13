import socket

_local_port: int | None = None


def get_ssh_redis_local_port() -> int:
    """Один свободный порт на 127.0.0.1 для SSH -L и redis-клиента (кэшируется)."""
    global _local_port
    if _local_port is None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            _local_port = s.getsockname()[1]
    return _local_port
