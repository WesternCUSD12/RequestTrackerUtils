{
  description = "Nix flake for Django Request Tracker Utils with a NixOS service module";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        lib = pkgs.lib;
      in
      {
        # Expose the NixOS module at the top level
        nixosModules = {
          requestTrackerUtils =
            {
              config,
              lib,
              pkgs,
              ...
            }:
            {
              options.services.requestTrackerUtils = {
                enable = lib.mkOption {
                  type = lib.types.bool;
                  default = false;
                  description = "Enable the Django Request Tracker Utils service.";
                };
                host = lib.mkOption {
                  type = lib.types.str;
                  default = "127.0.0.1";
                  description = "Host address for the Django app (Gunicorn binding).";
                };
                port = lib.mkOption {
                  type = lib.types.int;
                  default = 8000;
                  description = "Port for the Django app (Gunicorn binding).";
                };
                workers = lib.mkOption {
                  type = lib.types.int;
                  default = 4;
                  description = "Number of Gunicorn worker processes.";
                };
                secretsFile = lib.mkOption {
                  type = lib.types.path;
                  default = "/etc/request-tracker-utils/secrets.env";
                  description = "Path to the secrets environment file (must contain SECRET_KEY, RT_USERNAME, RT_PASSWORD).";
                };
                workingDirectory = lib.mkOption {
                  type = lib.types.str;
                  default = "/var/lib/request-tracker-utils";
                  description = "Working directory for the Django app service (contains database and media files).";
                };
                user = lib.mkOption {
                  type = lib.types.str;
                  default = "rtutils";
                  description = "User to run the Django app service as.";
                };
                group = lib.mkOption {
                  type = lib.types.str;
                  default = "rtutils";
                  description = "Group to run the Django app service as.";
                };
                labelWidthMm = lib.mkOption {
                  type = lib.types.int;
                  default = 100;
                  description = "Width of the label in millimeters.";
                };
                labelHeightMm = lib.mkOption {
                  type = lib.types.int;
                  default = 62;
                  description = "Height of the label in millimeters.";
                };
                rtUrl = lib.mkOption {
                  type = lib.types.str;
                  default = "https://tickets.wc-12.com";
                  description = "Request Tracker URL.";
                };
                apiEndpoint = lib.mkOption {
                  type = lib.types.str;
                  default = "/REST/2.0";
                  description = "API endpoint for Request Tracker.";
                };
                prefix = lib.mkOption {
                  type = lib.types.str;
                  default = "W12-";
                  description = "Prefix for asset tags.";
                };
                padding = lib.mkOption {
                  type = lib.types.int;
                  default = 4;
                  description = "Padding for labels.";
                };
                debug = lib.mkOption {
                  type = lib.types.bool;
                  default = false;
                  description = "Enable Django DEBUG mode (should be false in production).";
                };
                allowedHosts = lib.mkOption {
                  type = lib.types.listOf lib.types.str;
                  default = [ "localhost" "127.0.0.1" ];
                  description = "Django ALLOWED_HOSTS setting.";
                };
              };

              config = lib.mkIf config.services.requestTrackerUtils.enable {
                # Systemd service definition
                systemd.services.request-tracker-utils = {
                  description = "Django Request Tracker Utils service (Gunicorn)";
                  after = [ "network.target" ];
                  wantedBy = [ "multi-user.target" ];
                  
                  preStart = ''
                    # Create necessary directories
                    mkdir -p ${config.services.requestTrackerUtils.workingDirectory}/{static,media,logs}
                    
                    # Run Django migrations
                    cd ${self.packages.${system}.default}/lib/python*/site-packages
                    ${self.packages.${system}.default}/bin/python manage.py migrate --noinput
                    
                    # Collect static files
                    ${self.packages.${system}.default}/bin/python manage.py collectstatic --noinput --clear
                    
                    # Set proper permissions
                    chown -R ${config.services.requestTrackerUtils.user}:${config.services.requestTrackerUtils.group} ${config.services.requestTrackerUtils.workingDirectory}
                  '';
                  
                  serviceConfig = {
                    ExecStart = ''
                      ${self.packages.${system}.default}/bin/gunicorn \
                        --bind ${config.services.requestTrackerUtils.host}:${toString config.services.requestTrackerUtils.port} \
                        --workers ${toString config.services.requestTrackerUtils.workers} \
                        --timeout 120 \
                        --access-logfile ${config.services.requestTrackerUtils.workingDirectory}/logs/access.log \
                        --error-logfile ${config.services.requestTrackerUtils.workingDirectory}/logs/error.log \
                        --log-level info \
                        rtutils.wsgi:application
                    '';
                    
                    WorkingDirectory = config.services.requestTrackerUtils.workingDirectory;
                    Environment = [
                      "DJANGO_SETTINGS_MODULE=rtutils.settings"
                      "WORKING_DIR=${config.services.requestTrackerUtils.workingDirectory}"
                      "LABEL_WIDTH_MM=${toString config.services.requestTrackerUtils.labelWidthMm}"
                      "LABEL_HEIGHT_MM=${toString config.services.requestTrackerUtils.labelHeightMm}"
                      "RT_URL=${config.services.requestTrackerUtils.rtUrl}"
                      "API_ENDPOINT=${config.services.requestTrackerUtils.apiEndpoint}"
                      "PREFIX=${config.services.requestTrackerUtils.prefix}"
                      "PADDING=${toString config.services.requestTrackerUtils.padding}"
                      "DEBUG=${if config.services.requestTrackerUtils.debug then "True" else "False"}"
                      "ALLOWED_HOSTS=${lib.concatStringsSep "," config.services.requestTrackerUtils.allowedHosts}"
                      "STATIC_ROOT=${config.services.requestTrackerUtils.workingDirectory}/static"
                      "MEDIA_ROOT=${config.services.requestTrackerUtils.workingDirectory}/media"
                    ];
                    EnvironmentFile = config.services.requestTrackerUtils.secretsFile;
                    Restart = "always";
                    RestartSec = "10s";
                    User = config.services.requestTrackerUtils.user;
                    Group = config.services.requestTrackerUtils.group;
                    
                    # Security hardening
                    NoNewPrivileges = true;
                    PrivateTmp = true;
                    ProtectSystem = "strict";
                    ProtectHome = true;
                    ReadWritePaths = [ config.services.requestTrackerUtils.workingDirectory ];
                  };
                };

                # Ensure the user and group exist
                users.users.${config.services.requestTrackerUtils.user} = {
                  isSystemUser = true;
                  group = config.services.requestTrackerUtils.group;
                  home = config.services.requestTrackerUtils.workingDirectory;
                  createHome = true;
                };

                users.groups.${config.services.requestTrackerUtils.group} = { };

                # Create the working directory with proper permissions
                systemd.tmpfiles.rules = [
                  "d ${config.services.requestTrackerUtils.workingDirectory} 0750 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                  "d ${config.services.requestTrackerUtils.workingDirectory}/static 0755 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                  "d ${config.services.requestTrackerUtils.workingDirectory}/media 0750 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                  "d ${config.services.requestTrackerUtils.workingDirectory}/logs 0750 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                ];
              };
            };
        };

        # Package definition for the Django app
        packages = {
          default = pkgs.python3Packages.buildPythonApplication {
            pname = "request-tracker-utils";
            version = "0.4.0";
            pyproject = true;

            src = ./.;

            propagatedBuildInputs = with pkgs.python3Packages; [
              # Django and WSGI server
              django
              gunicorn
              
              # Core dependencies
              pandas
              requests
              reportlab
              qrcode
              python-barcode
              pillow
              
              # Google Admin SDK
              google-api-python-client
              google-auth
              google-auth-httplib2
              google-auth-oauthlib
            ];

            postInstall = ''
              # Copy Django project files
              mkdir -p $out/lib/python*/site-packages/rtutils
              cp -r rtutils/* $out/lib/python*/site-packages/rtutils/
              cp manage.py $out/lib/python*/site-packages/
              
              # Copy templates and static files
              mkdir -p $out/lib/python*/site-packages/templates
              cp -r templates/* $out/lib/python*/site-packages/templates/
              
              # Copy app templates
              for app in apps/*/templates; do
                if [ -d "$app" ]; then
                  cp -r "$app"/* $out/lib/python*/site-packages/templates/
                fi
              done
              
              # Set proper permissions
              chmod -R +r $out/lib/python*/site-packages
            '';

            meta = with pkgs.lib; {
              description = "Django application for Request Tracker asset management";
              license = lib.licenses.mit;
              maintainers = [ lib.maintainers.jmartinWestern ];
            };
          };
        };
      }
    );
}
