# NixOS Deployment Guide

## Overview

Request Tracker Utils is now a Django application deployed as a NixOS module using Gunicorn as the WSGI server. This guide covers deployment, configuration, and maintenance.

## Quick Start

### 1. Prerequisites

- NixOS system with flakes enabled
- Access to Request Tracker API credentials
- Domain name (optional, for production)

### 2. Enable Flakes

Add to your `/etc/nixos/configuration.nix`:

```nix
{
  nix.settings.experimental-features = [ "nix-command" "flakes" ];
}
```

### 3. Basic Configuration

See the complete example in `docs/deployment/nixos-module-example.nix`.

Minimal configuration:

```nix
{ config, ... }:

{
  services.requestTrackerUtils = {
    enable = true;
    host = "127.0.0.1";
    port = 8000;
    workers = 4;
    
    secretsFile = "/etc/request-tracker-utils/secrets.env";
    allowedHosts = [ "your-domain.com" "localhost" ];
    
    rtUrl = "https://tickets.wc-12.com";
  };
}
```

### 4. Create Secrets File

Generate a Django secret key:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Create `/etc/request-tracker-utils/secrets.env`:

```bash
SECRET_KEY=your-generated-secret-key-here
RT_USERNAME=your-rt-username
RT_PASSWORD=your-rt-password
```

Set permissions:

```bash
sudo chmod 400 /etc/request-tracker-utils/secrets.env
sudo chown rtutils:rtutils /etc/request-tracker-utils/secrets.env
```

### 5. Deploy

```bash
sudo nixos-rebuild switch
```

### 6. Verify

Check service status:

```bash
systemctl status request-tracker-utils
```

View logs:

```bash
journalctl -u request-tracker-utils -f
```

Access the application:

```bash
curl http://localhost:8000/
```

## Architecture

### Components

1. **Django Application**: Main web framework
2. **Gunicorn**: Production WSGI HTTP server
3. **SQLite Database**: Data storage (at `$WORKING_DIR/database.sqlite`)
4. **Static Files**: Served from `$WORKING_DIR/static/`
5. **Media Files**: User uploads at `$WORKING_DIR/media/`

### Service Flow

```
Client Request
    ↓
Nginx (optional reverse proxy)
    ↓
Gunicorn (port 8000)
    ↓
Django Application
    ↓
SQLite / RT API
```

## Configuration Options

### Network Settings

```nix
services.requestTrackerUtils = {
  host = "127.0.0.1";     # Bind address
  port = 8000;             # Listen port
  workers = 4;             # Gunicorn workers (2-4 × CPU cores)
};
```

### Security Settings

```nix
services.requestTrackerUtils = {
  secretsFile = "/path/to/secrets.env";
  debug = false;           # NEVER true in production
  allowedHosts = [
    "your-domain.com"
    "localhost"
  ];
};
```

### Data Storage

```nix
services.requestTrackerUtils = {
  workingDirectory = "/var/lib/request-tracker-utils";
  user = "rtutils";
  group = "rtutils";
};
```

Directory structure:
```
/var/lib/request-tracker-utils/
├── database.sqlite        # Django database
├── static/                # Collected static files
├── media/                 # User uploads
└── logs/
    ├── access.log         # Gunicorn access log
    └── error.log          # Gunicorn error log
```

### Label Configuration

```nix
services.requestTrackerUtils = {
  labelWidthMm = 100;      # Label width in mm
  labelHeightMm = 62;      # Label height in mm
  prefix = "W12-";         # Asset tag prefix
  padding = 4;             # Tag number padding
};
```

### Request Tracker Integration

```nix
services.requestTrackerUtils = {
  rtUrl = "https://tickets.wc-12.com";
  apiEndpoint = "/REST/2.0";
};
```

## Production Setup

### Nginx Reverse Proxy

Install and configure Nginx:

```nix
services.nginx = {
  enable = true;
  
  virtualHosts."rtutils.example.com" = {
    enableACME = true;
    forceSSL = true;
    
    locations."/" = {
      proxyPass = "http://127.0.0.1:8000";
      extraConfig = ''
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
      '';
    };
    
    locations."/static/" = {
      alias = "/var/lib/request-tracker-utils/static/";
    };
  };
};

networking.firewall.allowedTCPPorts = [ 80 443 ];
```

### Secret Management with agenix

1. Install agenix:

```nix
{
  imports = [ "${builtins.fetchTarball "https://github.com/ryantm/agenix/archive/main.tar.gz"}/modules/age.nix" ];
}
```

2. Create encrypted secrets:

```bash
agenix -e secrets.env.age
```

3. Configure:

```nix
age.secrets.rtutils-secrets = {
  file = ./secrets.env.age;
  owner = "rtutils";
  group = "rtutils";
};

services.requestTrackerUtils = {
  secretsFile = config.age.secrets.rtutils-secrets.path;
};
```

### Monitoring

```nix
# Prometheus monitoring
services.prometheus.exporters.nginx.enable = true;

# Email alerts on service failure
systemd.services.request-tracker-utils.serviceConfig = {
  OnFailure = "notify-failed@%n.service";
};
```

### Backups

```nix
services.restic.backups.rtutils = {
  paths = [ "/var/lib/request-tracker-utils" ];
  repository = "s3:s3.amazonaws.com/your-backup-bucket";
  passwordFile = "/etc/restic-password";
  s3CredentialsFile = "/etc/restic-s3-creds";
  
  timerConfig = {
    OnCalendar = "daily";
    Persistent = true;
  };
  
  pruneOpts = [
    "--keep-daily 7"
    "--keep-weekly 4"
    "--keep-monthly 6"
  ];
};
```

## Maintenance

### Updating the Application

```bash
# Pull latest changes
cd /path/to/RequestTrackerUtils
git pull

# Rebuild and switch
sudo nixos-rebuild switch
```

The `preStart` script automatically:
- Runs database migrations
- Collects static files
- Sets proper permissions

### Database Migrations

Manual migration (if needed):

```bash
sudo -u rtutils bash
cd /var/lib/request-tracker-utils
python manage.py migrate
```

### Viewing Logs

```bash
# Service logs
journalctl -u request-tracker-utils -f

# Gunicorn access log
sudo tail -f /var/lib/request-tracker-utils/logs/access.log

# Gunicorn error log
sudo tail -f /var/lib/request-tracker-utils/logs/error.log

# All logs from today
journalctl -u request-tracker-utils --since today
```

### Restarting the Service

```bash
sudo systemctl restart request-tracker-utils
```

### Checking Service Status

```bash
systemctl status request-tracker-utils
```

### Database Backup

```bash
# Manual backup
sudo cp /var/lib/request-tracker-utils/database.sqlite \
       /var/lib/request-tracker-utils/database.sqlite.backup-$(date +%Y%m%d)

# Automated with systemd timer
```

## Troubleshooting

### Service Won't Start

Check logs:
```bash
journalctl -u request-tracker-utils -n 50
```

Common issues:
- Missing secrets file
- Invalid SECRET_KEY
- Port already in use
- Database permissions

### Static Files Not Loading

Verify collection:
```bash
sudo -u rtutils python manage.py collectstatic --noinput
```

Check Nginx configuration serves `/static/` correctly.

### Database Errors

Reset migrations (CAUTION: destroys data):
```bash
sudo -u rtutils bash
cd /var/lib/request-tracker-utils
rm database.sqlite
python manage.py migrate
```

### Permission Errors

Fix ownership:
```bash
sudo chown -R rtutils:rtutils /var/lib/request-tracker-utils
sudo chmod 750 /var/lib/request-tracker-utils
```

## Security Considerations

1. **Never enable DEBUG in production**
   - Set `debug = false;`
   - Exposes sensitive information if true

2. **Protect secrets file**
   - Mode: 0400 or 0600
   - Owner: rtutils:rtutils
   - Use agenix/sops-nix for encryption

3. **Configure ALLOWED_HOSTS**
   - Only include your actual domains
   - Prevents host header attacks

4. **Use HTTPS in production**
   - Enable Nginx with Let's Encrypt
   - Force SSL/TLS

5. **Regular updates**
   - Keep NixOS and dependencies updated
   - Monitor security advisories

6. **Firewall configuration**
   - Only expose necessary ports
   - Use reverse proxy, not direct Django access

## Performance Tuning

### Gunicorn Workers

Formula: `(2 × CPU_cores) + 1`

```nix
services.requestTrackerUtils.workers = 5;  # For 2-core system
```

### Database Optimization

Consider PostgreSQL for production:

```nix
services.postgresql.enable = true;

# Update Django settings to use PostgreSQL
# Add psycopg2 to dependencies
```

### Caching

Add Redis for session/cache:

```nix
services.redis.servers."".enable = true;

# Configure Django to use Redis cache
```

## Migration from Flask

The Django migration is complete. Key differences:

1. **Port**: 5000 → 8000
2. **WSGI**: Flask built-in → Gunicorn
3. **Environment**: `FLASK_APP` → `DJANGO_SETTINGS_MODULE`
4. **Static files**: Now requires `collectstatic`
5. **Migrations**: Now automated via `manage.py migrate`

## Support

For issues or questions:
- GitHub: https://github.com/WesternCUSD12/RequestTrackerUtils
- Documentation: `/docs/` Guide

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
