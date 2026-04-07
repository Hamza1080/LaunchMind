import uuid
from datetime import datetime

_bus = {}  # dict: agent_name → list of messages

def send_message(msg_dict):
    required_fields = [
        "message_id",
        "from_agent",
        "to_agent",
        "message_type",
        "payload",
        "timestamp",
        "parent_message_id"
    ]

    # Validate message format
    for field in required_fields:
        if field not in msg_dict:
            raise ValueError(f"Missing required field: {field}")

    to = msg_dict["to_agent"]

    if to not in _bus:
        _bus[to] = []

    _bus[to].append(msg_dict)

    print(f"[{msg_dict['timestamp']}] {msg_dict['from_agent'].upper()} → {msg_dict['to_agent'].upper()}: {msg_dict['message_type']}")


def get_messages(agent_name):
    return _bus.get(agent_name, [])


def clear_messages(agent_name):
    _bus[agent_name] = []