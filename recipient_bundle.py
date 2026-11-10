"""Export only reviewed resume documents, excluding the private dossier evidence."""
import argparse
from io import BytesIO
from pathlib import Path
import zipfile

from application_dossier import MAX_DOSSIER_BYTES, verify_dossier_bytes
from safe_export import publish_bytes


def recipient_bytes(dossier, formats):
    verify_dossier_bytes(dossier)
    if not isinstance(formats, list) or not formats or len(formats) != len(set(formats)) or any(value not in ("txt", "html", "pdf") for value in formats):
        raise ValueError("Choose distinct resume formats: txt, html, pdf")
    output = BytesIO()
    with zipfile.ZipFile(BytesIO(dossier)) as source, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as target:
        for format in formats:
            name = "resume." + format
            if name not in source.namelist():
                raise ValueError("Selected resume format is unavailable: " + format)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            target.writestr(info, source.read(name))
    return output.getvalue()


def export_recipient_bundle(dossier, destination, formats, *, confirmed=False):
    if confirmed is not True:
        raise ValueError("Review the intended resume formats and confirm export")
    if Path(destination).suffix.lower() != ".zip":
        raise ValueError("Choose a .zip filename")
    payload = recipient_bytes(dossier, formats)
    publish_bytes(destination, payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dossier", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--formats", required=True, nargs="+", choices=("txt", "html", "pdf"))
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    with args.dossier.open("rb") as handle:
        payload = handle.read(MAX_DOSSIER_BYTES + 1)
    export_recipient_bundle(payload, args.output, args.formats, confirmed=args.confirm)


if __name__ == "__main__":
    main()
