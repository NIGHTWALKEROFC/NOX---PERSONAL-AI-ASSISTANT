import queue
import threading


class PasteSafeInput:
    """Reads terminal input line-by-line on a background thread. When several
    lines arrive close together (a paste), they're merged into ONE message
    instead of firing a separate send per line. 400ms window (up from 150ms)
    to reliably catch large pastes where chunk gaps can be bigger than that."""

    MERGE_WINDOW_SECONDS = 0.4

    def __init__(self):
        self._q = queue.Queue()
        self._thread = threading.Thread(target=self._reader, daemon=True)
        self._thread.start()

    def _reader(self):
        while True:
            try:
                line = input()
            except EOFError:
                self._q.put(None)
                break
            self._q.put(line)

    def get_message(self) -> str | None:
        first = self._q.get()
        if first is None:
            return None
        lines = [first]
        while True:
            try:
                nxt = self._q.get(timeout=self.MERGE_WINDOW_SECONDS)
            except queue.Empty:
                break
            if nxt is None:
                break
            lines.append(nxt)
        return "\n".join(lines).strip()
