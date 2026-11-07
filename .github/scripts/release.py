"""Version-matched release packaging and publication; credentials come from runner secrets."""

import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = "https://api.comfy.org"
REPOSITORY = "locomesa/comfyui-category-lora"


def project():
    with (ROOT / "pyproject.toml").open("rb") as stream:
        return tomllib.load(stream)


def release_version(tag):
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag):
        raise ValueError("Release tag must be vMAJOR.MINOR.PATCH.")
    config = project()
    if tag[1:] != config["project"]["version"]:
        raise ValueError("GitHub release tag does not match pyproject.toml version.")
    if config["project"]["name"] != "category-lora":
        raise ValueError("Unexpected registry package ID.")
    if config["tool"]["comfy"]["PublisherId"] != "locomesa":
        raise ValueError("Unexpected registry publisher.")
    return tag[1:]


def request_json(url, token=None, data=None, content_type="application/json"):
    headers = {"Accept": "application/json", "User-Agent": "category-lora-release"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if data is not None:
        headers["Content-Type"] = content_type
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        # Do not print request headers, credential values, or untrusted response bodies.
        raise RuntimeError(f"Release service returned HTTP {error.code}.") from None


def summary(message):
    print(message)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if destination:
        with open(destination, "a", encoding="utf-8") as stream:
            stream.write(message + "\n\n")


def build(tag):
    version = release_version(tag)
    destination = ROOT / "release-dist"
    destination.mkdir(exist_ok=True)
    filename = f"comfyui-category-lora-v{version}.zip"
    with zipfile.ZipFile(ROOT / "node.zip") as source:
        names = source.namelist()
        required = {
            "__init__.py",
            "policy.py",
            "presets.py",
            "pyproject.toml",
            "LICENSE",
            "LICENSE-Pixaroma.txt",
            "examples/category-controls-demo.json",
        }
        if not required.issubset(names):
            raise ValueError("Registry archive is missing required files.")
        for name in names:
            parts = name.replace("\\", "/").split("/")
            if name.startswith(("/", "\\")) or ".." in parts or ":" in name:
                raise ValueError("Unsafe archive path.")
            if parts[0] in {
                ".git",
                ".github",
                "tests",
                "docs",
                "assets",
                "release-dist",
                ".ruff_cache",
            }:
                raise ValueError("Development files unexpectedly included in archive.")
            if "__pycache__" in parts or parts[-1] in {
                "presets.json",
                "presets.json.bak",
            }:
                raise ValueError("Local runtime data unexpectedly included in archive.")
        with zipfile.ZipFile(
            destination / filename,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as output:
            for name in sorted(names):
                if name.endswith("/"):
                    continue
                entry = zipfile.ZipInfo(
                    "comfyui-category-lora/" + name, date_time=(2020, 1, 1, 0, 0, 0)
                )
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                output.writestr(entry, source.read(name))
    digest = hashlib.sha256((destination / filename).read_bytes()).hexdigest()
    (destination / "SHA256SUMS.txt").write_text(
        f"{digest}  {filename}\n", encoding="utf-8"
    )
    summary(
        f"Built {filename} with {len(names)} registry package entries. SHA-256: `{digest}`"
    )


def publish(tag):
    version = release_version(tag)
    versions = request_json(REGISTRY + "/nodes/category-lora/versions")
    existing = next((item for item in versions if item["version"] == version), None)
    if existing:
        summary(
            f"Registry version {version} already exists; upload skipped. Status: {existing['status']}."
        )
        return
    token = os.environ.pop("REGISTRY_ACCESS_TOKEN", "")
    if not token:
        raise ValueError("Repository secret REGISTRY_ACCESS_TOKEN is not configured.")
    from comfy_cli.command.custom_nodes.command import publish as publish_node

    publish_node(
        token=token,
        changelog=(ROOT / "RELEASE_NOTES.md").read_text(encoding="utf-8"),
        changelog_file=None,
    )
    summary(
        f"Uploaded Category LoRA {version} to [Comfy Registry](https://registry.comfy.org/nodes/category-lora). Registry scanning/approval is asynchronous; upload success is not approval."
    )


def upload_assets(tag):
    version = release_version(tag)
    token = os.environ.get("GH_TOKEN", "")
    if not token:
        raise ValueError("GitHub release upload token is unavailable.")
    release = request_json(
        f"https://api.github.com/repos/{REPOSITORY}/releases/tags/{tag}", token
    )
    if release.get("tag_name") != tag:
        raise ValueError("GitHub release tag mismatch.")
    assets = release.get("assets", [])
    for name in [f"comfyui-category-lora-v{version}.zip", "SHA256SUMS.txt"]:
        payload = (ROOT / "release-dist" / name).read_bytes()
        existing = next((asset for asset in assets if asset["name"] == name), None)
        if existing:
            digest = "sha256:" + hashlib.sha256(payload).hexdigest()
            if existing.get("digest") != digest:
                raise ValueError(
                    "An existing release asset differs; it will not be overwritten."
                )
            summary(f"GitHub asset {name} already matches; upload skipped.")
            continue
        upload_url = (
            release["upload_url"].split("{")[0] + "?name=" + urllib.parse.quote(name)
        )
        request_json(
            upload_url,
            token,
            payload,
            "application/zip" if name.endswith(".zip") else "text/plain",
        )
        summary(f"Attached {name} to GitHub release {tag}.")


if __name__ == "__main__":
    command = sys.argv[1]
    tag = os.environ.get("RELEASE_TAG", "")
    if command == "check":
        print("Validated release version:", release_version(tag))
    elif command == "build":
        build(tag)
    elif command == "publish":
        publish(tag)
    elif command == "upload":
        upload_assets(tag)
    else:
        raise SystemExit("Unknown release command.")
