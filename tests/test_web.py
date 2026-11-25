"""Cek antarmuka web: halaman utama tampil, API menjawab, input aneh ditolak."""

import pytest

from config.settings import DEFAULT_CORPUS_FILE

pytest.importorskip("flask")
pytestmark = pytest.mark.skipif(not DEFAULT_CORPUS_FILE.exists(), reason="korpus hasil preprocessing belum ada")


@pytest.fixture(scope="module")
def client():
    from web.app import create_app

    return create_app().test_client()


def test_halaman_utama_tampil(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Tanya isi Buku Pedoman Kurikulum 2024" in res.get_data(as_text=True)


def test_pertanyaan_sks_dijawab(client):
    res = client.post("/api/tanya", json={"question": "Berapa SKS mata kuliah Kecerdasan Artifisial?"})
    data = res.get_json()
    assert res.status_code == 200
    assert data["status"] == "answered"
    assert "2 SKS" in data["answer"]
    assert data["source"]["pdf_page"]
    assert len(data["trace"]["candidates"]) >= 1


def test_pertanyaan_kosong_ditolak(client):
    res = client.post("/api/tanya", json={"question": "   "})
    assert res.status_code == 400
    assert "error" in res.get_json()


def test_pertanyaan_terlalu_panjang_ditolak(client):
    res = client.post("/api/tanya", json={"question": "a" * 1000})
    assert res.status_code == 400


def test_pertanyaan_di_luar_buku_tidak_dijawab(client):
    res = client.post("/api/tanya", json={"question": "Siapa rektor Universitas Brawijaya?"})
    data = res.get_json()
    assert data["status"] == "not_found"
    assert data["confidence"] < data["threshold"]
