# Example NixOS configuration for deploying Request Tracker Utils
#
# Add this to your NixOS configuration.nix or as a separate module

{ config, pkgs, ... }:

{
  # Import the flake module
  imports = [
    # Adjust path to your flake location
    # Option 1: From local path
    # /path/to/RequestTrackerUtils/flake.nix
    
    # Option 2: From flake inputs (recommended)
    # Add to your system flake.nix inputs:
    # inputs.request-tracker-utils.url = "github:WesternCUSD12/RequestTrackerUtils/005-django-refactor";
    # Then import: inputs.request-tracker-utils.nixosModules.requestTrackerUtils
  ];

  # Enable the service
  services.requestTrackerUtils = {
    enable = true;
    
    # Network settings
    host = "127.0.0.1";  # Bind to localhost (use reverse proxy for external access)
    port = 8000;          # Django app port
    workers = 4;          # Number of Gunicorn workers (adjust based on CPU cores)
    
    # Security settings
    secretsFile = "/etc/request-tracker-utils/secrets.env";
    debug = false;        # NEVER enable in production
    allowedHosts = [
      "tickets.wc-12.com"
      "rtutils.wc-12.com"
      "localhost"
      "127.0.0.1"
    ];
    
    # Data storage
    workingDirectory = "/var/lib/request-tracker-utils";
    user = "rtutils";
    group = "rtutils";
    
    # Label configuration
    labelWidthMm = 100;
    labelHeightMm = 62;
    
    # Request Tracker API
    rtUrl = "https://tickets.wc-12.com";
    apiEndpoint = "/REST/2.0";
    prefix = "W12-";
    padding = 4;
  };

  # Create the secrets file (must contain):
  # - SECRET_KEY=your-django-secret-key-here
  # - RT_USERNAME=your-rt-username
  # - RT_PASSWORD=your-rt-password
  #
  # Generate a SECRET_KEY with:
  # python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
  
  # Recommended: Use agenix or sops-nix for secret management
  # Example with plain file (NOT recommended for production):
  environment.etc."request-tracker-utils/secrets.env" = {
    text = ''
      SECRET_KEY=your-secret-key-here-change-this-in-production
      RT_USERNAME=your-rt-username
      RT_PASSWORD=your-rt-password
    '';
    mode = "0400";
    user = "rtutils";
    group = "rtutils";
  };

  # Optional: Nginx reverse proxy configuration
  services.nginx = {
    enable = true;
    
    recommendedProxySettings = true;
    recommendedTlsSettings = true;
    recommendedOptimisation = true;
    recommendedGzipSettings = true;
    
    virtualHosts."rtutils.wc-12.com" = {
      enableACME = true;  # Let's Encrypt SSL
      forceSSL = true;
      
      locations."/" = {
        proxyPass = "http://127.0.0.1:8000";
        proxyWebsockets = true;
        extraConfig = ''
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
          
          # Increase timeout for long-running label generation
          proxy_read_timeout 300s;
          proxy_connect_timeout 300s;
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

  # Optional: Firewall configuration
  networking.firewall.allowedTCPPorts = [ 80 443 ];

  # Optional: Automated backups with restic
  services.restic.backups.rtutils = {
    paths = [ "/var/lib/request-tracker-utils" ];
    repository = "/backup/rtutils";
    passwordFile = "/etc/restic-password";
    timerConfig = {
      OnCalendar = "daily";
      Persistent = true;
    };
  };

  # Optional: Log rotation
  services.logrotate.settings.rtutils = {
    files = "/var/lib/request-tracker-utils/logs/*.log";
    frequency = "daily";
    rotate = 14;
    compress = true;
    delaycompress = true;
    missingok = true;
    notifempty = true;
    create = "0640 rtutils rtutils";
  };
}
