from uuid import uuid4


def generate_request_id() -> str:
    return f"req_{uuid4().hex}"


def generate_session_id() -> str:
    return f"ses_{uuid4().hex}"