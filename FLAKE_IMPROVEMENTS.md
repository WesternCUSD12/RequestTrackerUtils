# Flake.nix Improvements

## Issues Fixed

### 1. **Missing Django Apps Directory**
- **Problem**: The `apps/` directory containing all Django apps (audit, assets, devices, students, labels, authentication, common) was not being copied to the package
- **Fix**: Added `cp -r apps/* $SITE_PACKAGES/apps/` to postInstall

### 2. **Missing Common Utilities**
- **Problem**: The `common/` directory with shared utilities (RT API, configuration helpers) was not included
- **Fix**: Added `cp -r common/* $SITE_PACKAGES/common/` to postInstall

### 3. **Incorrect Project Structure**
- **Problem**: Code referenced old `request_tracker_utils` instead of Django `rtutils` project
- **Fix**: Updated paths to use `rtutils` correctly

### 4. **Missing Static Files**
- **Problem**: Static files from project root and apps were not being copied
- **Fix**: Added comprehensive static file copying with app-specific handling

### 5. **Missing Build Dependencies**
- **Problem**: setuptools and wheel were not listed as build dependencies
- **Fix**: Added `nativeBuildInputs` with setuptools and wheel

### 6. **Hardcoded Python Version Paths**
- **Problem**: Used `python*/` wildcard which doesn't work reliably in Nix
- **Fix**: Changed to `${pkgs.python3.libPrefix}` which correctly resolves to `python3.12`

### 7. **Missing Runtime Dependencies**
- **Problem**: Missing ldap3, django-extensions, python-dotenv, click
- **Fix**: Added all missing dependencies from pyproject.toml

### 8. **Broken Package in nixpkgs**
- **Problem**: postgresql-test-hook marked as broken in nixpkgs-unstable
- **Fix**: Added `config.allowBroken = true` to pkgs import

### 9. **Incorrect preStart Paths**
- **Problem**: manage.py path was wrong, missing PYTHONPATH setup
- **Fix**: Added proper PYTHONPATH and corrected paths to use `${pkgs.python3.libPrefix}`

## Example NixOS Configuration

```nix
# /etc/nixos/configuration.nix
{ config, pkgs, ... }:

let
  rtutils-flake = builtins.getFlake "github:WesternCUSD12/RequestTrackerUtils/007-unified-student-data";
in
{
  imports = [
    ./hardware-configuration.nix
    rtutils-flake.nixosModules.requestTrackerUtils
  ];

  # Enable the Request Tracker Utils service
  services.requestTrackerUtils = {
    enable = true;
    
    # Network configuration
    host = "0.0.0.0";  # Listen on all interfaces
    port = 8000;
    
    # Performance tuning
    workers = 8;  # Adjust based on CPU cores (2x cores is typical)
    
    # File paths
    workingDirectory = "/var/lib/request-tracker-utils";
    secretsFile = "/etc/request-tracker-utils/secrets.env";
    
    # Service account
    user = "rtutils";
    group = "rtutils";
    
    # Label configuration
    labelWidthMm = 100;
    labelHeightMm = 62;
    
    # Request Tracker integration
    rtUrl = "https://tickets.wc-12.com";
    apiEndpoint = "/REST/2.0";
    
    # Asset tag configuration
    prefix = "W12-";
    padding = 4;
    
    # Security
    debug = false;  # NEVER enable in production
    allowedHosts = [ 
      "rtutils.wc-12.com" 
      "tickets.wc-12.com"
      "localhost"
    ];
  };
  
  # Nginx reverse proxy (recommended for production)
  services.nginx = {
    enable = true;
    
    recommendedProxySettings = true;
    recommendedTlsSettings = true;
    recommendedOptimisation = true;
    recommendedGzipSettings = true;
    
    virtualHosts."rtutils.wc-12.com" = {
      enableACME = true;  # Free SSL via Let's Encrypt
      forceSSL = true;
      
      locations."/" = {
        proxyPass = "http://127.0.0.1:8000";
        proxyWebsockets = true;
        extraConfig = ''
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
          
          # Timeouts for large file uploads
          proxy_read_timeout 300s;
          proxy_connect_timeout 75s;
        '';
      };
      
      locations."/static/" = {
        alias = "/var/lib/request-tracker-utils/static/";
        extraConfig = ''
          expires 30d;
          add_header Cache-Control "public, immutable";
        '';
      };
      
      locations."/media/" = {
        alias = "/var/lib/request-tracker-utils/media/";
        extraConfig = ''
          expires 7d;
          add_header Cache-Control "public";
        '';
      };
    };
  };
  
  # Security: ACME certificates for SSL
  security.acme = {
    acceptTerms = true;
    defaults.email = "admin@wc-12.com";
  };
  
  # Firewall configuration
  networking.firewall = {
    allowedTCPPorts = [ 80 443 ];
  };
  
  # Create secrets file (do this manually for security)
  # /etc/request-tracker-utils/secrets.env should contain:
  # SECRET_KEY=your-very-long-random-secret-key-here
  # RT_USERNAME=your-rt-api-username
  # RT_PASSWORD=your-rt-api-password
  # LDAP_BIND_PASSWORD=your-ldap-password (if using LDAP auth)
  
  system.stateVersion = "24.11";
}
```

## Setting Up Secrets

```bash
# On the NixOS server, create the secrets directory
sudo mkdir -p /etc/request-tracker-utils
sudo chmod 750 /etc/request-tracker-utils

# Create the secrets file
sudo nano /etc/request-tracker-utils/secrets.env

# Add these lines (replace with actual values):
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
RT_USERNAME=your_rt_api_username
RT_PASSWORD=your_rt_api_password
LDAP_BIND_DN=cn=admin,dc=wc-12,dc=com
LDAP_BIND_PASSWORD=your_ldap_password

# Secure the file
sudo chmod 640 /etc/request-tracker-utils/secrets.env
sudo chown root:rtutils /etc/request-tracker-utils/secrets.env
```

## Deployment Commands

```bash
# Build the flake locally
nix build .# --impure

# Deploy to NixOS server
sudo nixos-rebuild switch --flake .#

# Or from Git repository
sudo nixos-rebuild switch --flake github:WesternCUSD12/RequestTrackerUtils/007-unified-student-data

# Check service status
sudo systemctl status request-tracker-utils

# View logs
sudo journalctl -u request-tracker-utils -f

# Restart service after config changes
sudo systemctl restart request-tracker-utils
```

## Development vs Production

### Development (devenv)
```bash
# Current development setup using devenv
devenv shell
uv run python manage.py runserver
```

### Production (NixOS service)
- Runs via Gunicorn (production WSGI server)
- Behind Nginx reverse proxy
- SSL/TLS encryption via Let's Encrypt
- Systemd service management
- Automatic restarts on failure
- Proper file permissions and security hardening
- Centralized logging via journald

## Performance Tuning

### Workers Configuration
```nix
workers = (num_cores * 2) + 1;
# Example: 4 cores = 9 workers
# Example: 8 cores = 17 workers
```

### Database Optimization
For production, consider migrating from SQLite to PostgreSQL:

```nix
services.postgresql = {
  enable = true;
  ensureDatabases = [ "rtutils" ];
  ensureUsers = [{
    name = "rtutils";
    ensureDBOwnership = true;
  }];
};

# Then in secrets.env:
DATABASE_URL=postgresql://rtutils@localhost/rtutils
```

## Monitoring

```nix
# Add Prometheus monitoring
services.prometheus = {
  enable = true;
  exporters.node.enable = true;
};

# Add Grafana for visualization
services.grafana = {
  enable = true;
  settings.server = {
    http_addr = "127.0.0.1";
    http_port = 3000;
  };
};
```

## Backup Strategy

```nix
# Automatic backups using systemd timers
systemd.services.rtutils-backup = {
  script = ''
    #!/bin/sh
    BACKUP_DIR=/var/backups/rtutils
    mkdir -p $BACKUP_DIR
    
    # Backup database
    cp /var/lib/request-tracker-utils/database.sqlite \
       $BACKUP_DIR/database-$(date +%Y%m%d-%H%M%S).sqlite
    
    # Keep only last 30 days
    find $BACKUP_DIR -name "database-*.sqlite" -mtime +30 -delete
  '';
  
  serviceConfig = {
    Type = "oneshot";
    User = "rtutils";
  };
};

systemd.timers.rtutils-backup = {
  wantedBy = [ "timers.target" ];
  timerConfig = {
    OnCalendar = "daily";
    Persistent = true;
  };
};
```
