"""Entry point CLI untuk Sistem QA Kurikulum 2024 Teknik Informatika UB."""

import argparse
import json

from config.settings import DEFAULT_CORPUS_FILE, DEFAULT_KB_FILE


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
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Jalankan evaluasi 20 pertanyaan acuan dan simpan hasilnya ke reports/evaluation_results.csv.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Tampilkan output lengkap (termasuk top kandidat) dalam format JSON.",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Jalankan antarmuka web di http://127.0.0.1:<port> (butuh Flask).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Port untuk mode --web (bawaan 5000).",
    )
    return parser.parse_args()


def load_index():
    """Baca passage & fakta tabel hasil preprocessing, lalu bangun indeks retrieval (sekali saja)."""
    from src.retrieval.index_builder import build_index

    def read_jsonl(path):
        with open(path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    passages = read_jsonl(DEFAULT_CORPUS_FILE)
    triples = read_jsonl(DEFAULT_KB_FILE) if DEFAULT_KB_FILE.exists() else None
    return build_index(passages, triples=triples)


def format_answer(output: dict) -> str:
    """Jawaban + sumber dalam bentuk yang enak dibaca di terminal."""
    lines = [f"Jawaban : {output['answer']}"]
    source = output.get("source")
    if output.get("status") == "answered" and source:
        where = f"hal. PDF {source.get('pdf_page')} (hal. dokumen {source.get('doc_page')})"
        detail = source.get("table_title") or source.get("section")
        lines.append(f"Sumber  : {where}" + (f" — {detail}" if detail else ""))
        lines.append(f"Keyakinan: {output.get('confidence', 0):.2f}")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    if not DEFAULT_CORPUS_FILE.exists():
        print(
            f"[INFO] Korpus belum tersedia di {DEFAULT_CORPUS_FILE}.\n"
            "Jalankan modul Anggota 1 (document_ingestion) dan Anggota 2 (preprocessing) terlebih dahulu."
        )
        return

    if args.web:
        from web.app import create_app

        print("Menyiapkan indeks dan server web...")
        app = create_app()
        print(f"Buka http://127.0.0.1:{args.port} di browser. Tekan Ctrl+C untuk berhenti.")
        app.run(host="127.0.0.1", port=args.port, debug=False)
        return

    from src.pipeline.qa_pipeline import answer_question

    print("Menyiapkan indeks...")
    index = load_index()

    if args.evaluate:
        from src.pipeline.evaluation import run_evaluation

        summary = run_evaluation(answer_fn=lambda q: answer_question(q, index=index))
        print(f"Benar/Salah : {summary['n_correct']}/{summary['n_wrong']} dari {summary['n_questions']} soal")
        print(f"Accuracy    : {summary['accuracy']:.2%}")
        print(f"MRR         : {summary['mrr']:.4f}")
        print("Detail per soal tersimpan di reports/evaluation_results.csv")
        return

    def ask(question: str) -> None:
        output = answer_question(question, index=index)
        print(json.dumps(output, ensure_ascii=False, indent=2) if args.json else format_answer(output))

    if args.question:
        ask(args.question)
        return

    print("Ketik pertanyaan tentang Kurikulum 2024 TIF UB (kosongkan lalu Enter untuk keluar).")
    while True:
        try:
            question = input("\nPertanyaan: ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break
        if not question:
            break
        ask(question)


if __name__ == "__main__":
    main()
