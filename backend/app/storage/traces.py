import json
from pathlib import Path

from app.models.trace import TraceRecord


class TraceStore:
    def __init__(self, directory: str):
        self.directory = Path(directory)
        self.directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.path = self.directory / "requests.jsonl"

    def append(
        self,
        trace: TraceRecord,
    ) -> None:
        payload = trace.model_dump(mode="json")

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as file:
            file.write(
                json.dumps(
                    payload,
                    separators=(",", ":"),
                )
            )
            file.write("\n")

    def read_all(self) -> list[TraceRecord]:
        if not self.path.exists():
            return []

        traces = []

        with self.path.open(
            "r",
            encoding="utf-8",
        ) as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                payload = json.loads(line)

                traces.append(
                    TraceRecord.model_validate(
                        payload
                    )
                )

        return traces