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
        pkgs = import nixpkgs {
          inherit system;
          config.allowBroken = true;
        };
        lib = pkgs.lib;

        # Define the package here so it's available to the module
        requestTrackerPackage = pkgs.python3Packages.buildPythonApplication {
          pname = "request-tracker-utils";
          version = "0.4.0";
          format = "pyproject";

          src = ./.;

          nativeBuildInputs = with pkgs.python3Packages; [
            setuptools
            wheel
          ] ++ [ pkgs.makeWrapper ];

          propagatedBuildInputs = with pkgs.python3Packages; [
            # Django and WSGI server
            django
            gunicorn
            django-extensions
            django-import-export
            tablib
            whitenoise

            # Core dependencies
            pandas
            requests
            reportlab
            qrcode
            python-barcode
            pillow
            python-dotenv
            click
            sqlparse

            # LDAP authentication
            ldap3
            asgiref

            # Google Admin SDK
            google-api-python-client
            google-auth
            google-auth-httplib2
            google-auth-oauthlib
          ];



          meta = with pkgs.lib; {
            description = "Django application for Request Tracker asset management";
            license = lib.licenses.mit;
            maintainers = [ ];
          };
        };
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
                  type = lib.types.nullOr lib.types.path;
                  default = null;
                  description = "Optional environment file for additional secrets (sourced by systemd).";
                };
                secretKey = lib.mkOption {
                  type = lib.types.nullOr lib.types.str;
                  default = null;
                  description = "Secret key for Django; if null a persistent key is generated under workingDirectory.";
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
                  default = [
                    "localhost"
                    "127.0.0.1"
                  ];
                  description = "Django ALLOWED_HOSTS setting.";
                };
                rtToken = lib.mkOption {
                  type = lib.types.str;
                  description = "Request Tracker API token.";
                };
                ldapServer = lib.mkOption {
                  type = lib.types.str;
                  description = "LDAP server URI (e.g., ldaps://dc.example.com:636).";
                };
                ldapBaseDn = lib.mkOption {
                  type = lib.types.str;
                  description = "LDAP base DN.";
                };
                ldapUpnSuffix = lib.mkOption {
                  type = lib.types.nullOr lib.types.str;
                  default = null;
                  description = "Optional LDAP UPN suffix.";
                };
                ldapTechGroup = lib.mkOption {
                  type = lib.types.str;
                  default = "tech-team";
                  description = "LDAP group for technology staff.";
                };
                ldapTeacherGroup = lib.mkOption {
                  type = lib.types.str;
                  default = "TEACHERS";
                  description = "LDAP group for teachers.";
                };
                ldapVerifyCert = lib.mkOption {
                  type = lib.types.bool;
                  default = true;
                  description = "Whether to verify LDAP TLS certificates.";
                };
                ldapCaCertFile = lib.mkOption {
                  type = lib.types.nullOr lib.types.path;
                  default = null;
                  description = "Optional CA bundle for LDAP TLS.";
                };
                ldapTimeout = lib.mkOption {
                  type = lib.types.int;
                  default = 10;
                  description = "LDAP timeout in seconds.";
                };
              };

              config = lib.mkIf config.services.requestTrackerUtils.enable (
                let
                  cfg = config.services.requestTrackerUtils;

                  # Single source of truth for all python dependencies
                  pythonDependencies = with pkgs.python3Packages; [
                    requestTrackerPackage # The application itself

                    # Runtime dependencies
                    gunicorn
                    pandas
                    requests
                    django
                    django-extensions
                    django-import-export
                    whitenoise
                    click
                    reportlab
                    qrcode
                    python-barcode
                    pillow
                    python-dotenv
                    google-api-python-client
                    google-auth
                    google-auth-oauthlib
                    google-auth-httplib2
                    ldap3

                    # Transitive dependencies that were causing issues
                    tablib
                    sqlparse
                    asgiref
                  ];

                  # Create a complete, self-contained Python environment
                  pythonEnv = pkgs.python3.withPackages (ps: pythonDependencies);

                  manageBin = "${requestTrackerPackage}/bin/rtutils-manage";

                  generateSecretKeyScript = pkgs.writeScript "generate-secret-key" ''
                    #!${pkgs.bash}/bin/bash
                    set -e
                    TEMP_ENV_FILE="$1"
                    PYTHON_BIN="$2"

                    if ! grep -q "^DJANGO_SECRET_KEY=" "$TEMP_ENV_FILE"; then
                      echo "DJANGO_SECRET_KEY not found, generating a new one."
                      GENERATED_KEY=$("$PYTHON_BIN" -c 'import secrets; print(secrets.token_urlsafe(40))')
                      printf "DJANGO_SECRET_KEY=%s\n" "$GENERATED_KEY" >> "$TEMP_ENV_FILE"
                    fi
                  '';
                in
                {
                  # Secrets (RT token, LDAP credentials, etc.) are expected to
                  # be provided via the runtime `secretsFile` (sops) and are
                  # sourced in `preStart` and ExecStart. Do not require them
                  # at Nix evaluation time so secrets can remain out-of-band.

                  systemd.services.request-tracker-utils = {
                    description = "Django Request Tracker Utils service (Gunicorn)";
                    after = [ "network.target" ];
                    wantedBy = [ "multi-user.target" ];

                    environment.PATH = lib.mkForce "${pkgs.lib.makeBinPath [
                      pythonEnv # Provides python, gunicorn, etc.
                      pkgs.coreutils
                      pkgs.bash
                      pkgs.sops
                      pkgs.gnugrep
                      pkgs.gnused
                    ]}";

                    preStart =
                      let
                        workDir = cfg.workingDirectory;
                        user = cfg.user;
                        group = cfg.group;
                        envFile = "/run/${user}/secrets.env"; # The single source of truth for secrets
                      in
                      ''
                        set -e
                        echo "--- rtutils pre-start ---"

                        # 1. Prepare directories
                        mkdir -p "${workDir}/static" "${workDir}/media" "${workDir}/logs"

                        # 2. Prepare environment file
                        echo "Preparing environment file at ${envFile}"
                        tempEnvFile=$(mktemp)

                        # If a secrets file is provided, decrypt or copy it.
                        ${lib.optionalString (cfg.secretsFile != null) ''
                          if ${pkgs.sops}/bin/sops -d "${cfg.secretsFile}" > /dev/null 2>&1; then
                            echo "Decrypting sops file: ${cfg.secretsFile}"
                            ${pkgs.sops}/bin/sops -d "${cfg.secretsFile}" > "$tempEnvFile"
                          else
                            echo "Copying plaintext secrets file: ${cfg.secretsFile}"
                            cp "${cfg.secretsFile}" "$tempEnvFile"
                          fi
                        ''}

                        # 3. Ensure DJANGO_SECRET_KEY exists, generating if needed.
                        "${generateSecretKeyScript}" "$tempEnvFile" "${pythonEnv}/bin/python"

                        # 4. Finalize the environment file
                        mv "$tempEnvFile" "${envFile}"
                        chmod 0600 "${envFile}"
                        chown ''${user}:''${group} "${envFile}"

                        # 5. Source the environment for pre-start tasks
                        # Sanitize and source the environment file to handle .env formats
                        set -a
                        source <(grep -v '^#' "${envFile}" | sed 's/[[:space:]]*=[[:space:]]*/=/g')
                        set +a

# 6. Run Django management commands
                         SITE_PACKAGES=$(${pythonEnv}/bin/python -c "import site; print(site.getsitepackages()[0])")
                         export PYTHONPATH="$SITE_PACKAGES"
                         echo "PYTHONPATH is: $PYTHONPATH"
                         echo "Contents of site-packages:"
                         ls -l "$SITE_PACKAGES"
                         cd "${workDir}"
                         echo "Running Django migrations..."
                         ${requestTrackerPackage}/bin/rtutils-manage migrate --noinput
                         echo "Collecting static files..."
                         ${requestTrackerPackage}/bin/rtutils-manage collectstatic --noinput --clear

                        # 7. Set final permissions
                        chown -R ''${user}:''${group} "${workDir}"
                        echo "--- rtutils pre-start complete ---"
                      '';

                    serviceConfig =
                      let
                        workDir = cfg.workingDirectory;
                        envFile = "/run/${cfg.user}/secrets.env";
                      in
                      {
                        # Load all secrets securely using systemd's EnvironmentFile directive.
                        EnvironmentFile = "-${envFile}";

                        # The ExecStart command now uses the gunicorn from our complete pythonEnv
                         ExecStart = "${requestTrackerPackage}/bin/rtutils-gunicorn";


                        WorkingDirectory = cfg.workingDirectory;
                        RuntimeDirectory = "rtutils";
                         Environment = [
                           "DJANGO_SETTINGS_MODULE=rtutils.settings"
                           # Ensure Gunicorn can import rtutils from the Nix store
                           "PYTHONPATH=$(${pythonEnv}/bin/python -c 'import site; print(site.getsitepackages()[0])')"
                           "WORKING_DIR=${cfg.workingDirectory}"
                           "LABEL_WIDTH_MM=${toString cfg.labelWidthMm}"
                           "LABEL_HEIGHT_MM=${toString cfg.labelHeightMm}"
                           "RT_URL=${cfg.rtUrl}"
                           "API_ENDPOINT=${cfg.apiEndpoint}"
                           "PREFIX=${cfg.prefix}"
                           "PADDING=${toString cfg.padding}"
                           "DEBUG=${if cfg.debug then "True" else "False"}"
                           "ALLOWED_HOSTS=${lib.concatStringsSep "," cfg.allowedHosts}"
                           "STATIC_ROOT=${cfg.workingDirectory}/static"
                           "MEDIA_ROOT=${cfg.workingDirectory}/media"
                         ]
                         ++ lib.optional (
                           cfg.ldapCaCertFile != null
                         ) "LDAP_CA_CERT_FILE=${cfg.ldapCaCertFile}";

                        Restart = "always";
                        RestartSec = "10s";
                        User = cfg.user;
                        Group = cfg.group;

                        NoNewPrivileges = true;
                        PrivateTmp = true;
                        ProtectSystem = "strict";
                        ProtectHome = true;
                        ReadWritePaths = [ cfg.workingDirectory ];
                      };
                  };

                  users.users.${config.services.requestTrackerUtils.user} = {
                    isSystemUser = true;
                    group = config.services.requestTrackerUtils.group;
                    home = config.services.requestTrackerUtils.workingDirectory;
                    createHome = true;
                  };

                  users.groups.${config.services.requestTrackerUtils.group} = { };

                  systemd.tmpfiles.rules = [
                    "d ${config.services.requestTrackerUtils.workingDirectory} 0750 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                    "d ${config.services.requestTrackerUtils.workingDirectory}/static 0755 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                    "d ${config.services.requestTrackerUtils.workingDirectory}/media 0750 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                    "d ${config.services.requestTrackerUtils.workingDirectory}/logs 0750 ${config.services.requestTrackerUtils.user} ${config.services.requestTrackerUtils.group} -"
                  ];
                }
              );
            };
        };

        packages = {
          default = requestTrackerPackage;
        };
      }
    );
}
