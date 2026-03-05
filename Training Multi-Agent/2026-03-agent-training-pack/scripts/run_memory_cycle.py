import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Dict


@dataclass
class Observation:
    timestamp: str
    scene: str
    cell_type: str
    salience: float
    content: Dict


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def observer(uncompressed_events: List[Dict]) -> List[Observation]:
    observations: List[Observation] = []
    for event in uncompressed_events:
        observations.append(
            Observation(
                timestamp=now_iso(),
                scene=event.get("scene", "general"),
                cell_type=event.get("cell_type", "fact"),
                salience=float(event.get("salience", 0.5)),
                content={"summary": event.get("text", "")[:200]}
            )
        )
    return observations


def reflector(observations: List[Observation]) -> List[Observation]:
    best_by_scene: Dict[str, Observation] = {}
    for obs in observations:
        prev = best_by_scene.get(obs.scene)
        if prev is None or obs.salience >= prev.salience:
            best_by_scene[obs.scene] = obs
    return list(best_by_scene.values())


def demo() -> None:
    raw_events = [
        {"scene": "shopify", "cell_type": "decision", "salience": 0.9, "text": "Use approval gate before publishing posts."},
        {"scene": "shopify", "cell_type": "task", "salience": 0.7, "text": "Add auto-summary after article generation."},
        {"scene": "security", "cell_type": "risk", "salience": 0.95, "text": "Do not expose API key in logs."},
        {"scene": "security", "cell_type": "fix", "salience": 0.8, "text": "Move key loading into .env and runtime injection."}
    ]

    observed = observer(raw_events)
    reflected = reflector(observed)

    print("=== Observed ===")
    print(json.dumps([asdict(x) for x in observed], indent=2, ensure_ascii=False))

    print("\n=== Reflected (condensed) ===")
    print(json.dumps([asdict(x) for x in reflected], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    demo()
