"""Lightweight in-process pub/sub event bus used to keep GUI pages in sync."""

TOPIC_SERVERS = "servers"
TOPIC_HISTORY = "history"
TOPIC_TUNNELS = "tunnels"
TOPIC_KEYS = "keys"
TOPIC_COMMANDS = "commands"
TOPIC_SETTINGS = "settings"
TOPIC_SESSIONS = "sessions"


class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list] = {}

    def subscribe(self, topic: str, callback) -> None:
        self._subscribers.setdefault(topic, []).append(callback)

    def unsubscribe(self, topic: str, callback) -> None:
        subs = self._subscribers.get(topic, [])
        if callback in subs:
            subs.remove(callback)

    def publish(self, topic: str, payload=None) -> None:
        for callback in list(self._subscribers.get(topic, [])):
            try:
                callback(payload)
            except Exception:  # subscriber errors must never break publishers
                import logging

                logging.getLogger("ssh_desk.events").exception("event subscriber failed")
