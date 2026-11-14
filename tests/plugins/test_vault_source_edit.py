import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

import plugins.vault.dashboard.plugin_api as api
from workstation.vault import VaultManager


def test_nested_source_roundtrip_and_stale_edit(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    nested = root / "Projects"
    nested.mkdir(parents=True)
    original = b"---\r\ntitle: Draft\r\naliases: [Alias]\r\n---\r\n\r\n# Draft\r\n\r\n[[Target]]\r\n"
    source = nested / "Draft.md"
    source.write_bytes(original)
    manager = VaultManager(str(root))
    monkeypatch.setattr(api, "_vault_manager", manager)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)

    opened = client.get("/notes/Projects/Draft.md")
    assert opened.status_code == 200
    assert opened.json()["note"]["content"].encode() == original
    old_revision = opened.json()["note"]["revision"]
    assert old_revision == hashlib.sha256(original).hexdigest()

    new_content = opened.json()["note"]["content"] + "\r\nChanged without flattening YAML.\r\n"
    saved = client.put("/notes/Projects/Draft.md", json={"content": new_content, "expected_revision": old_revision})
    assert saved.status_code == 200, saved.text
    assert source.read_bytes() == new_content.encode()
    assert not (root / "Draft.md").exists()
    assert saved.json()["note"]["revision"] != old_revision

    source.write_bytes(b"edited externally")
    collision = client.put("/notes/Projects/Draft.md", json={"content": "unsafe overwrite", "expected_revision": old_revision})
    assert collision.status_code == 409
    assert source.read_bytes() == b"edited externally"


def test_source_edit_rejects_unsafe_paths(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    manager = VaultManager(str(root))
    monkeypatch.setattr(api, "_vault_manager", manager)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    response = client.put("/notes/../outside.md", json={"content": "bad", "expected_revision": "a" * 64})
    assert response.status_code in (400, 404)
    assert not (tmp_path / "outside.md").exists()

def test_create_only_rejects_existing_title_without_modifying_bytes(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    nested = root / "Projects"
    nested.mkdir(parents=True)
    original = b"---\ntitle: Existing\n---\n\nKeep all content.\n"
    existing = nested / "Existing.md"
    existing.write_bytes(original)
    manager = VaultManager(str(root))
    monkeypatch.setattr(api, "_vault_manager", manager)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)

    response = client.post("/notes", json={
        "title": "Existing", "content": "Should never replace it", "create_only": True,
    })
    assert response.status_code == 409
    assert existing.read_bytes() == original
    assert not (root / "Existing.md").exists()

    created = client.post("/notes", json={
        "title": "New Note", "content": "[[Existing]]", "create_only": True,
    })
    assert created.status_code == 200
    assert (root / "New Note.md").exists()


def test_source_edit_refuses_title_collision(tmp_path, monkeypatch):
    root = tmp_path / "vault"
    root.mkdir()
    original = b"---\ntitle: Alpha\n---\n\nOriginal\n"
    (root / "Alpha.md").write_bytes(original)
    (root / "Beta.md").write_text("---\ntitle: Beta\n---\n", encoding="utf-8")
    manager = VaultManager(str(root))
    monkeypatch.setattr(api, "_vault_manager", manager)
    app = FastAPI()
    app.include_router(api.router)
    client = TestClient(app)
    opened = client.get("/notes/Alpha")
    revision = opened.json()["note"]["revision"]

    result = client.put("/notes/Alpha.md", json={
        "content": "---\ntitle: Beta\n---\n\nOverwritten?",
        "expected_revision": revision,
    })
    assert result.status_code == 400
    assert (root / "Alpha.md").read_bytes() == original
