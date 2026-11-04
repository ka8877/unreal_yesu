"""Packaging/security tests only. PE/container fixtures are not Unreal builds."""

from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "Gospel/prepare_preview_release.py"
SPEC = importlib.util.spec_from_file_location("gospel_release", SCRIPT)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)
COMMIT = "a" * 40
OTHER_COMMIT = "b" * 40
SOURCE_IDENTITY = release.source_identity


class GospelReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root / "packaged"
        self.output = self.root / "release"
        self.campaign = self.root / "Campaign.json"
        self.campaign.write_text(json.dumps({
            "SchemaVersion": 1, "CampaignId": "gospel-pilgrimage", "ContentVersion": 1,
            "Source": {"Repository": "ka8877/firstgame", "Commit": OTHER_COMMIT},
            "Quests": [{"Id": qid, "ChapterId": "temple"} for qid in release.PREVIEW_QUESTS],
        }), encoding="utf-8")
        # Minimum header fixture used to exercise packaging rules. No executable
        # code is generated or run, and the archive below is never a game build.
        fake_pe = bytearray(134)
        fake_pe[:2] = b"MZ"
        struct.pack_into("<I", fake_pe, 60, 128)
        fake_pe[128:] = b"PE\0\0\x64\x86"
        self.exe = self.write("Windows/PathOfDawnUnreal/Binaries/Win64/PathOfDawnUnreal.exe", fake_pe)
        self.pak = self.write("Windows/PathOfDawnUnreal/Content/Paks/Gospel-Windows.pak", b"packaging test fixture; not cooked Unreal content" + struct.pack("<II", 0x5A6F12E1, 11))
        self.source = {"commit": COMMIT, "dirty": False, "identityMethod": "supplied-commit", "packagingHead": COMMIT}
        self.identity = patch.object(release, "source_identity", return_value=self.source)
        self.identity.start()
        self.addCleanup(self.identity.stop)

    def write(self, name, data):
        path = self.build / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(bytes(data))
        return path

    def prepare(self, **changes):
        args = dict(build_root=self.build, output=self.output, build_id="preview-001", campaign_path=self.campaign, commit=COMMIT)
        args.update(changes)
        return release.prepare(**args)

    def make_smoke(self):
        result = self.prepare()
        manifest = json.loads(Path(result["manifest"]).read_text())
        evidence = self.root / "observations"
        evidence.mkdir()
        captures = []
        for i in range(6):
            # Image signature fixtures check copying/hash association only.
            image = evidence / f"capture-{i}.png"
            image.write_bytes(b"\x89PNG\r\n\x1a\n" + bytes([i]) * 20)
            captures.append({"path": image.name, "sha256": release.digest_file(image)})
        report = {
            "buildId": manifest["buildId"], "sourceCommit": COMMIT,
            "payloadSha256": manifest["payloadSha256"], "campaignSha256": manifest["campaign"]["sha256"],
            "map": release.PREVIEW_MAP, "previewQuestIds": list(release.PREVIEW_QUESTS),
            "evidenceKind": "actual-unreal-graphical", "tester": "Fixture for schema tests only",
            "engineVersion": "5.8.4", "testedUtc": "2026-11-04T08:00:00Z",
            "checks": {key: True for key in release.SMOKE_CHECKS}, "captures": captures,
        }
        path = evidence / "smoke.json"
        path.write_text(json.dumps(report), encoding="utf-8")
        return path, report

    def test_candidate_contains_explicit_gospel_launcher_and_no_public_claim(self):
        result = self.prepare()
        manifest = json.loads(Path(result["manifest"]).read_text())
        self.assertEqual(result["status"], "candidate-not-graphically-verified")
        self.assertFalse(manifest["validation"]["publicReady"])
        self.assertEqual(manifest["validation"]["hostedDeployment"], "not-performed")
        self.assertIsNone(manifest["graphicalSmoke"])
        with zipfile.ZipFile(result["archive"]) as archive:
            command = archive.read("PLAY-GOSPEL.cmd").decode()
            self.assertIn(release.PREVIEW_MAP, command)
            self.assertNotIn("L_Galilee", command)
            self.assertIn("Binaries\\Win64\\PathOfDawnUnreal.exe", command)
            self.assertEqual(json.loads(archive.read("preview-manifest.json")), manifest)
            self.assertIn("do not need Unreal Editor or Visual Studio", archive.read("README-GOSPEL.txt").decode())
            for row in manifest["files"]:
                self.assertEqual(release.digest_bytes(archive.read(row["path"])), row["sha256"])

    def test_same_inputs_produce_deterministic_zip_and_payload(self):
        one = self.prepare()
        two = self.prepare(output=self.root / "second")
        self.assertEqual(Path(one["archive"]).read_bytes(), Path(two["archive"]).read_bytes())
        self.assertEqual(one["payloadSha256"], two["payloadSha256"])

    def test_iostore_requires_matching_nonempty_files(self):
        self.pak.unlink()
        self.write("Windows/PathOfDawnUnreal/Content/Paks/Gospel.utoc", b"-==--==--==--==-" + b"toc fixture")
        with self.assertRaisesRegex(release.ReleaseError, "Incomplete IoStore"):
            self.prepare()
        self.write("Windows/PathOfDawnUnreal/Content/Paks/Gospel.ucas", b"data fixture")
        self.assertEqual(self.prepare()["status"], "candidate-not-graphically-verified")

    def test_rejects_corrupt_pak_footer_and_iostore_toc_header(self):
        self.pak.write_bytes(b"corrupt pak fixture")
        with self.assertRaisesRegex(release.ReleaseError, "PAK footer"):
            self.prepare()
        self.pak.unlink()
        self.write("Windows/PathOfDawnUnreal/Content/Paks/Gospel.utoc", b"corrupt toc fixture")
        self.write("Windows/PathOfDawnUnreal/Content/Paks/Gospel.ucas", b"data fixture")
        with self.assertRaisesRegex(release.ReleaseError, "TOC signature"):
            self.prepare()

    def test_rejects_empty_or_absent_cooked_payload(self):
        self.pak.write_bytes(b"")
        with self.assertRaisesRegex(release.ReleaseError, "Empty cooked"):
            self.prepare()
        self.pak.unlink()
        with self.assertRaisesRegex(release.ReleaseError, "No cooked"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_rejects_invalid_windows_executable(self):
        self.exe.write_bytes(b"not a PE file")
        with self.assertRaisesRegex(release.ReleaseError, "DOS/PE"):
            self.prepare()

    def test_rejects_ambiguous_executables(self):
        self.write("Windows/PathOfDawnUnreal/Binaries/Win64/PathOfDawnUnreal-Shipping.exe", self.exe.read_bytes())
        with self.assertRaisesRegex(release.ReleaseError, "exactly one"):
            self.prepare()

    def test_rejects_private_or_saved_files_instead_of_silently_uploading(self):
        for name in ["Windows/Saved/progress.sav", ".env", "Windows/key.pem", "Windows/.aws/config", "Windows/logs/session.txt"]:
            with self.subTest(name=name):
                path = self.write(name, b"private fixture")
                with self.assertRaises(release.ReleaseError):
                    self.prepare()
                path.unlink()
                parent = path.parent
                while parent != self.build and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                self.assertFalse(self.output.exists())

    def test_rejects_nonempty_credentials_in_runtime_configuration(self):
        self.write("Windows/Config/provider.ini", b"[Provider]\nApiKey=private-test-fixture\n")
        with self.assertRaisesRegex(release.ReleaseError, "Possible credential"):
            self.prepare()

    def test_rejects_links_and_windows_path_collisions(self):
        link = self.build / "linked.pak"
        link.symlink_to(self.pak)
        with self.assertRaisesRegex(release.ReleaseError, "Symbolic links"):
            self.prepare()
        link.unlink()
        self.write("Windows/asset.dat", b"a")
        self.write("Windows/ASSET.dat", b"b")
        with self.assertRaisesRegex(release.ReleaseError, "collision"):
            self.prepare()

    def test_refuses_existing_output_and_output_inside_build(self):
        self.output.mkdir()
        protected = self.output / "user.txt"
        protected.write_text("preserve")
        with self.assertRaisesRegex(release.ReleaseError, "already exists"):
            self.prepare()
        self.assertEqual(protected.read_text(), "preserve")
        with self.assertRaisesRegex(release.ReleaseError, "contain each other"):
            self.prepare(output=self.build / "output")
        with self.assertRaisesRegex(release.ReleaseError, "contain each other"):
            self.prepare(output=self.root / "other" / ".." / "packaged" / "output")

    def test_rejects_corrupt_campaign_and_wrong_preview(self):
        self.campaign.write_text('{"SchemaVersion":1,"SchemaVersion":1}')
        with self.assertRaisesRegex(release.ReleaseError, "Duplicate JSON"):
            self.prepare()
        self.campaign.write_text('{"SchemaVersion":1,"CampaignId":"old-luke5"}')
        with self.assertRaisesRegex(release.ReleaseError, "schema/id"):
            self.prepare()

    def test_build_receipt_cannot_claim_other_commit_or_changed_files(self):
        path = self.write("gospel-build-manifest.json", json.dumps({"buildId": "preview-001", "sourceCommit": OTHER_COMMIT}).encode())
        with self.assertRaisesRegex(release.ReleaseError, "sourceCommit mismatch"):
            self.prepare()
        row = {"path": self.pak.relative_to(self.build).as_posix(), "bytes": self.pak.stat().st_size, "sha256": "0" * 64}
        path.write_text(json.dumps({"buildId": "preview-001", "sourceCommit": COMMIT, "files": [row]}))
        with self.assertRaisesRegex(release.ReleaseError, "Manifest file changed"):
            self.prepare()

    def test_legacy_build_receipt_payload_hash_is_checked(self):
        rows, _ = release.inventory(self.build)
        legacy = "\n".join(row["path"] + "\t" + row["sha256"].upper() for row in rows)
        manifest = {"buildId": "preview-001", "payloadSha256": release.digest_bytes(legacy.encode())}
        path = self.write("build-manifest.json", json.dumps(manifest).encode())
        self.prepare()
        manifest["payloadSha256"] = "0" * 64
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(release.ReleaseError, "payload changed"):
            self.prepare(output=self.root / "second")

    def test_unfilled_smoke_template_cannot_be_used_as_evidence(self):
        result = self.prepare()
        template = Path(result["manifest"]).parent / "graphical-smoke.template.json"
        self.assertEqual(json.loads(template.read_text())["evidenceKind"], "not-performed")
        with self.assertRaisesRegex(release.ReleaseError, "actual Unreal graphical"):
            self.prepare(output=self.root / "attested", smoke_report=template)

    def test_attested_evidence_is_bound_and_copied_but_not_public_ready(self):
        smoke, _ = self.make_smoke()
        result = self.prepare(output=self.root / "attested", smoke_report=smoke)
        self.assertEqual(result["status"], "graphical-smoke-attested")
        manifest = json.loads(Path(result["manifest"]).read_text())
        self.assertFalse(manifest["validation"]["publicReady"])
        with zipfile.ZipFile(result["archive"]) as archive:
            self.assertIn("evidence/graphical-smoke.json", archive.namelist())
            self.assertEqual(len(manifest["graphicalSmoke"]["captures"]), 6)

    def test_smoke_rejects_crosscommit_stale_payload_and_false_checks(self):
        smoke, valid = self.make_smoke()
        changes = [{"sourceCommit": OTHER_COMMIT}, {"payloadSha256": "0" * 64}, {"map": "/Game/PathOfDawn/Maps/L_Galilee"}, {"checks": {key: False for key in release.SMOKE_CHECKS}}]
        for changed in changes:
            with self.subTest(changed=changed):
                smoke.write_text(json.dumps(valid | changed))
                with self.assertRaises(release.ReleaseError):
                    self.prepare(output=self.root / "attested", smoke_report=smoke)
                self.assertFalse((self.root / "attested").exists())

    def test_modified_capture_traversal_and_duplicate_images_are_refused(self):
        smoke, valid = self.make_smoke()
        valid["captures"][0]["path"] = "../Campaign.json"
        smoke.write_text(json.dumps(valid))
        with self.assertRaisesRegex(release.ReleaseError, "Unsafe archive path"):
            self.prepare(output=self.root / "attested", smoke_report=smoke)
        valid["captures"][0] = dict(valid["captures"][1])
        smoke.write_text(json.dumps(valid))
        with self.assertRaisesRegex(release.ReleaseError, "duplicate image"):
            self.prepare(output=self.root / "attested", smoke_report=smoke)

    def test_dirty_source_cannot_be_upgraded_by_a_smoke_report(self):
        smoke, _ = self.make_smoke()
        self.source["dirty"] = True
        with self.assertRaisesRegex(release.ReleaseError, "dirty source"):
            self.prepare(output=self.root / "attested", smoke_report=smoke)

    def test_change_during_zip_writing_aborts_without_partial_release(self):
        original = release.check_build_receipt
        def mutate(*args):
            original(*args)
            self.pak.write_bytes(b"changed after inventory")
        with patch.object(release, "check_build_receipt", side_effect=mutate):
            with self.assertRaisesRegex(release.ReleaseError, "Input changed"):
                self.prepare()
        self.assertFalse(self.output.exists())

    def test_archive_paths_reject_traversal_drive_names_and_device_names(self):
        for path in ["../escape", "/absolute", "C:/drive", "dir\\escape", "dir/../escape", "dir/CON.txt", "dir/file."]:
            with self.subTest(path=path), self.assertRaises(release.ReleaseError):
                release.safe_relative(path)

    def test_cli_refuses_bad_build_id_without_creating_output(self):
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            code = release.main(["--build-root", str(self.build), "--output", str(self.output), "--build-id", "bad&command", "--campaign", str(self.campaign), "--source-commit", COMMIT])
        self.assertEqual(code, 1)
        self.assertFalse(self.output.exists())

    def test_source_identity_requires_full_commit_and_records_git_dirty_state(self):
        with self.assertRaisesRegex(release.ReleaseError, "full 40-character"):
            SOURCE_IDENTITY("short", self.root)
        with patch.object(release.subprocess, "run") as run:
            run.side_effect = [type("Git", (), {"stdout": COMMIT + "\n"})(), type("Git", (), {"stdout": " M source.cpp\n"})()]
            source = SOURCE_IDENTITY(None, self.root)
        self.assertEqual(source["commit"], COMMIT)
        self.assertTrue(source["dirty"])


if __name__ == "__main__":
    unittest.main()
