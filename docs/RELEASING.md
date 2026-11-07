# Releasing Category LoRA

The package ID is `category-lora`, the publisher is `locomesa`, and the GitHub repository is `locomesa/comfyui-category-lora`.

## One-time setup

Store the Comfy Registry publishing key as the repository's Actions secret named `REGISTRY_ACCESS_TOKEN`. It permits publishing under this publisher; never commit it or print its value. The workflow uses GitHub's automatically issued token only to attach assets to the current repository's release.

## Each release

1. Update `project.version` in `pyproject.toml` to a new three-part version. Published registry versions cannot be overwritten.
2. Update `CHANGELOG.md`, `RELEASE_NOTES.md`, and any user documentation affected by the change. Document compatibility limits honestly.
3. Run `comfy node validate`, the README's behavior tests, and appropriate live ComfyUI checks when runtime code changes.
4. Commit all required files. `comfy node pack` uses tracked files; `.comfyignore` removes development files. Keep both license notices and the web directory.
5. Create a GitHub release tagged `v` followed by the exact package version, targeting that commit. Copy `RELEASE_NOTES.md` into its description. Keep prereleases marked as such while compatibility testing is limited.
6. Publish that GitHub release. The release workflow validates the matching version, runs tests, builds the installer ZIP and checksum, attaches them to the GitHub release, and uploads the same package version to Comfy Registry.
7. Check the workflow result and registry status. `Pending` means the upload has not yet cleared registry scanning. Do not claim immediate Manager availability. Share the GitHub installer ZIP while registry availability is pending.

To retry an interrupted release, use Actions > Release to GitHub and Comfy Registry > Run workflow and enter the existing release tag. Matching assets and existing registry versions are skipped; differing existing assets are never silently overwritten. An existing flagged/banned version still needs the registry's review process and is not repaired by rerunning publication.

## Package contents and credentials

Runtime Python files, frontend modules, README, changelog, metadata, the example and both licenses ship in the registry package. Tests, automation, design assets and this release guide stay on GitHub. Personal presets, model weights and local credentials must never be included.

The manual ZIP uses one enclosing `comfyui-category-lora` directory. A Manager install may use a different folder name: keep only one installed copy. User presets are stored separately in ComfyUI's user directory.
