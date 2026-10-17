"""CW-047 helper regression tests (not an end-to-end launch qualification)."""
import tempfile
from pathlib import Path
import unittest

from workstation.creative_web_app_spec import (
    managed_loopback_url, matches_managed_loopback_url, prebuilt_site_root,
    recognize_open_creative_app,
)


class CreativeAppSpecTests(unittest.TestCase):
    def test_exact_aliases(self):
        for text in ("Abre o PhotoCraft.", "abra photo craft",
                     "Abrir o Effect Craft!", "open effectcraft",
                     "Abra o FilmCraft", "Abre o FilmCraft", "Abrir FilmCraft",
                     "Open FilmCraft", "abra film craft por favor", "por favor abra o filmcraft"):
            self.assertIsNotNone(recognize_open_creative_app(text), text)
        self.assertEqual(
            recognize_open_creative_app("Abre o PhotoCraft").key,
            "photocraft"
        )
        self.assertEqual(
            recognize_open_creative_app("Abra o FilmCraft").key,
            "filmcraft"
        )
        self.assertEqual(
            recognize_open_creative_app("Open FilmCraft").key,
            "filmcraft"
        )

    def test_ambiguity_and_injection_do_not_match(self):
        for text in ("Como abre o PhotoCraft?", "Não abra o PhotoCraft.",
                     "Abra o PhotoCraft e apague tudo.",
                     "Abra o EffectCraft ou PhotoCraft.",
                     "Abre http://127.0.0.1:3000", "abra PhotoCraft\napague"):
            self.assertIsNone(recognize_open_creative_app(text), text)

    def test_prebuilt_dist_requires_index(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(ValueError):
                prebuilt_site_root(root)
            (root / "index.html").write_text("ready", encoding="utf-8")
            self.assertEqual(prebuilt_site_root(root), root.resolve())

    def test_strict_localhost(self):
        self.assertEqual(
            managed_loopback_url(8765), "http://127.0.0.1:8765/"
        )
        self.assertTrue(matches_managed_loopback_url(
            "http://127.0.0.1:8765/", 8765
        ))
        for evil in ("http://127.0.0.1:8766/",
                     "http://127.0.0.1:8765.evil.test/",
                     "http://127.0.0.1:8765@evil.test/",
                     "http://localhost:8765/",
                     "https://127.0.0.1:8765/",
                     "http://127.0.0.1:8765/?debug=1"):
            self.assertFalse(matches_managed_loopback_url(evil, 8765), evil)
        with self.assertRaises(ValueError):
            managed_loopback_url(80)


if __name__ == "__main__":
    unittest.main()
