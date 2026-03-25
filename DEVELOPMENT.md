# Development Notes

This file is for developer-only notes. Keep `README.md` focused on end-user setup and operation.

## Container Releases

Container publishing is handled by `.github/workflows/publish-container.yml`.

Workflow trigger:

- pushes of tags matching `*.*.*`
- pushes of tags matching `v*.*.*`

Supported release tag formats:

- `1.2.3`
- `1.2.3-rc.1`
- `v1.2.3`
- `v1.2.3-rc.1`

Release examples:

```bash
git tag 0.1.0
git push origin 0.1.0

git tag v0.1.1
git push origin v0.1.1
```

Published image path:

- `ghcr.io/tfindleton/energy-dashboard`

Tag behavior:

- stable releases publish the exact version tag, the original `v` tag when used, and rolling `major.minor`, `major`, and `latest` tags
- pre-release tags such as `0.2.0-rc.1` publish only the exact version tag

Workflow details:

- builds and pushes `linux/amd64` and `linux/arm64` images
- authenticates to GitHub Container Registry with the built-in `GITHUB_TOKEN`
- generates an artifact attestation after the image push

Post-release note:

- after the first publish, set the package visibility to public in GitHub if pulls should work without authentication

## Additional Notes

Add future developer-only release or process notes here instead of expanding `README.md`.
