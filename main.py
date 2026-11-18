"""Entry point CLI untuk Sistem QA Kurikulum 2024 Teknik Informatika UB."""

import argparse
import json

from config.settings import DEFAULT_CORPUS_FILE


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sistem QA Kurikulum 2024 Teknik Informatika UB (Classic NLP)"
    )
    parser.add_argument(
        "--question",
        "-q",
        type=str,
        help="Pertanyaan yang ingin diajukan ke sistem QA.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not DEFAULT_CORPUS_FILE.exists():
        print(
            f"[INFO] Korpus belum tersedia di {DEFAULT_CORPUS_FILE}.\n"
            "Jalankan modul Anggota 1 (document_ingestion) dan Anggota 2 (preprocessing) terlebih dahulu."
        )
        return

    if args.question:
        print(json.dumps({"question": args.question, "status": "pipeline_not_connected"}, indent=2))
    else:
        print("Mode interaktif siap dihubungkan ke src.pipeline.qa_pipeline.answer_question().")


if __name__ == "__main__":
    main()
