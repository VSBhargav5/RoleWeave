"""Seed only a new empty practice shelf with explicitly synthetic examples."""
import json

from runtime_paths import RESOURCE_ROOT


def seed_practice(store):
    if store.list_jobs() or store.list_profiles() or store.list_resumes():
        raise ValueError("Practice examples require an empty shelf; existing data was not changed")
    store.save_profile((RESOURCE_ROOT / "examples" / "career-profile.json").read_bytes())
    source = (RESOURCE_ROOT / "examples" / "synthetic.json").read_bytes()
    india = store.save(source, "Synthetic Data Engineer", "Synthetic Example Co", "https://example.invalid/india")
    data = json.loads(source)
    data["market"] = "relocation"
    data["posting"] = "Synthetic relocation role. Python required. Production Spark operations required. Sponsorship and work authorization are unverified."
    store.save(json.dumps(data).encode(), "Synthetic Relocation Engineer", "Synthetic International Co", "https://example.invalid/relocation")
    return india
