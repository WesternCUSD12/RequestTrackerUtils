# NixOS Deployment Guide

_Last updated: 2025-10-13_

## Overview

This runbook documents how the RequestTrackerUtils Flask service is packaged and deployed via NixOS using the flake module exposed from `flake.nix`. Follow these steps whenever reorganizing code or updating configuration as part of feature `002-ensure-my-flask`.

## Module Reference

- Flake module: `self.nixosModules.requestTrackerUtils`
- Service name: `request-tracker-utils`
- Systemd unit: `systemd.services.request-tracker-utils`
- Package entrypoint: `${self.packages.${system}.default}/bin/request-tracker-utils`

### Service Options

| Option                                | Default                                  | Description                                                    |
| ------------------------------------- | ---------------------------------------- | -------------------------------------------------------------- |
| `services.requestTrackerUtils.enable` | `false`                                  | Toggle the service.                                            |
| `host`                                | `127.0.0.1`                              | Bind address for the Flask server.                             |
| `port`                                | `5000`                                   | HTTP port exposed by the service.                              |
| `secretsFile`                         | `/etc/request-tracker-utils/secrets.env` | Environment file containing sensitive tokens (RT token, etc.). |
| `workingDirectory`                    | `/var/lib/request-tracker-utils`         | Instance directory for DB, logs, and cache.                    |
| `user` / `group`                      | `rtutils`                                | Dedicated service account created by the module.               |
| `labelWidthMm` / `labelHeightMm`      | `100` / `62`                             | Overrides for label dimensions.                                |
| `rtUrl`                               | `https://tickets.wc-12.com`              | Base RT instance URL.                                          |
| `apiEndpoint`                         | `/REST/2.0`                              | RT REST API endpoint.                                          |
| `prefix`                              | `W12-`                                   | Asset tag prefix.                                              |
| `padding`                             | `4`                                      | Label padding in millimeters.                                  |

## Deployment Steps

1. Update code and documentation on feature branch.
2. Rebuild local package to ensure flake still evaluates:
   ```fish
   nix build .#request-tracker-utils
   ```
3. For staging/production hosts, run:
   ```fish
   sudo nixos-rebuild switch --flake /etc/nixos#request-tracker-utils
   ```
4. Confirm service status:
   ```fish
   sudo systemctl status request-tracker-utils
   ```
5. Tail logs to verify structured logging format (post Phase 4 implementation):
   ```fish
   sudo journalctl -u request-tracker-utils -f
   ```

## Validation Checklist

- [ ] Flake builds successfully (`nix flake check` or `nix build`).
- [ ] Service restarts without errors after applying `nixos-rebuild`.
- [ ] Environment variables (RT token, etc.) resolved via `EnvironmentFile`.
- [ ] Application reachable on configured host/port.
- [ ] Log output matches structured logging contract.

## Rollback Procedure

- Execute `sudo nixos-rebuild switch --rollback` to revert to the previous generation.
- If configuration-only change caused failure, adjust `/etc/nixos/` module configuration and re-run rebuild.
- Notify stakeholders via release notes (`docs/releases/002-ensure-my-flask.md` once authored).

## Related Artefacts

- `flake.nix` / `flake.lock`
- `devenv.nix`
- `specs/002-ensure-my-flask/quickstart.md` (Phase 2 validation matrix)
