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
          ];

          propagatedBuildInputs = with pkgs.python3Packages; [
            # Django and WSGI server
            django
            gunicorn
            django-extensions
            django-import-export
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

            # LDAP authentication
            ldap3
            asgiref

            # Google Admin SDK
            google-api-python-client
            google-auth
            google-auth-httplib2
            google-auth-oauthlib
          ];

          postInstall = ''
                        SITE_PACKAGES=$out/lib/${pkgs.python3.libPrefix}/site-packages

                        # Copy Django project settings
                        mkdir -p $SITE_PACKAGES/rtutils
                        cp -r rtutils/* $SITE_PACKAGES/rtutils/

                        # Copy all Django apps
                        mkdir -p $SITE_PACKAGES/apps
                        cp -r apps/* $SITE_PACKAGES/apps/

                        # Copy common utilities
                        mkdir -p $SITE_PACKAGES/common
                        cp -r common/* $SITE_PACKAGES/common/

                        # Copy manage.py
                        cp manage.py $SITE_PACKAGES/

                        # Copy all templates (project-level and app-level)
                        mkdir -p $SITE_PACKAGES/templates
                        if [ -d templates ]; then
                          cp -r templates/* $SITE_PACKAGES/templates/
                        fi

                        # Copy all static files
                        mkdir -p $SITE_PACKAGES/static
                        if [ -d static ]; then
                          cp -r static/* $SITE_PACKAGES/static/
                        fi

                        # Copy app-specific static files
                        for app in apps/*/static; do
                          if [ -d "$app" ]; then
                            cp -r "$app"/* $SITE_PACKAGES/static/
                          fi
                        done

                        # Provide a helper for manage.py that uses the packaged interpreter
                        mkdir -p $out/bin
                        # Render the wrapper from the template in the source tree.
                        mkdir -p $out/bin
                        sed \
                          -e "s|@SITE_PACKAGES@|$out/lib/${pkgs.python3.libPrefix}/site-packages|g" \
                          -e "s|@PYTHON_BIN@|${pkgs.python3}/bin/python|g" \
                          ${./scripts/rtutils-manage.template} > $out/bin/rtutils-manage
                        chmod +x $out/bin/rtutils-manage

                        chmod -R +r $SITE_PACKAGES
          '';

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
                  sitePkgs = "${requestTrackerPackage}/lib/${pkgs.python3.libPrefix}/site-packages";
                  manageBin = "${requestTrackerPackage}/bin/rtutils-manage";
                  secretEnvFile = "${config.services.requestTrackerUtils.workingDirectory}/secret.env";
                  pythonPath = pkgs.lib.makeSearchPath "lib/${pkgs.python3.libPrefix}/site-packages" (
                    [ requestTrackerPackage ]
                    ++ (with pkgs.python3Packages; [
                      django
                      gunicorn
                      django-extensions
                      django-import-export
                      whitenoise
                      pandas
                      requests
                      reportlab
                      qrcode
                      python-barcode
                      pillow
                      python-dotenv
                      click
                      ldap3
                      asgiref
                      google-api-python-client
                      google-auth
                      google-auth-httplib2
                      google-auth-oauthlib
                    ])
                  );
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
                      requestTrackerPackage
                      pkgs.python3
                      pkgs.coreutils
                      pkgs.bash
                      pkgs.sops
                    ]}";

                    preStart =
                      let
                        workDir = config.services.requestTrackerUtils.workingDirectory;
                        user = config.services.requestTrackerUtils.user;
                        group = config.services.requestTrackerUtils.group;
                        providedSecret = config.services.requestTrackerUtils.secretKey;
                        secretLines =
                          if config.services.requestTrackerUtils.secretsFile != null then
                            [
                              # Decrypt and source the secrets using bash so process-substitution works.
                              "${pkgs.bash}/bin/bash -c 'set -a; if ${pkgs.sops}/bin/sops -d ${config.services.requestTrackerUtils.secretsFile} >/dev/null 2>&1; then . <(${pkgs.sops}/bin/sops -d ${config.services.requestTrackerUtils.secretsFile}); else echo \"sops decryption failed\" >&2; fi; set +a'"
                            ] else if providedSecret == null then
                            [
                              "${pkgs.python3}/bin/python - <<'PY' > ${secretEnvFile}"
                              "import secrets, string"
                              "alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'"
                              "key = ''.join(secrets.choice(alphabet) for _ in range(50))"
                              "print(f'DJANGO_SECRET_KEY={key}')"
                              "PY"
                            ]
                          else
                            [
                              "printf 'DJANGO_SECRET_KEY=%s\\n' '${providedSecret}' > ${secretEnvFile}"
                            ];
                      in
                      (lib.concatStringsSep "\n" (
                        [
                          "mkdir -p ${workDir}/static"
                          "mkdir -p ${workDir}/media"
                          "mkdir -p ${workDir}/logs"
                        ]
                        ++ secretLines
                        ++ [
                          "chmod 640 ${secretEnvFile}"
                          "chown ${user}:${group} ${secretEnvFile}"
                          "set -a"
                          "if [ -f ${secretEnvFile} ]; then . ${secretEnvFile}; fi"
                          "set +a"
                          "export PYTHONPATH=${pythonPath}"
                          "cd ${workDir}"
                          "${manageBin} migrate --noinput"
                          "${manageBin} collectstatic --noinput --clear"
                          "chown -R ${user}:${group} ${workDir}"
                        ]
                      ))
                      + "\n";

                    serviceConfig =
                      let
                        gunicornBin = "${pkgs.python3Packages.gunicorn}/bin/gunicorn";
                        host = config.services.requestTrackerUtils.host;
                        port = toString config.services.requestTrackerUtils.port;
                        workers = toString config.services.requestTrackerUtils.workers;
                        workDir = config.services.requestTrackerUtils.workingDirectory;
                        envSources = lib.concatStringsSep " " (
                          [ "[ -f ${secretEnvFile} ] && . ${secretEnvFile}" ]
                          ++
                            lib.optional (config.services.requestTrackerUtils.secretsFile != null)
                              "[ -f ${config.services.requestTrackerUtils.secretsFile} ] && . ${config.services.requestTrackerUtils.secretsFile}"
                        );
                      in
                      {
                        ExecStart = "${pkgs.bash}/bin/bash -c 'set -a; ${envSources}; set +a; exec ${gunicornBin} --bind ${host}:${port} --workers ${workers} --timeout 120 --access-logfile ${workDir}/logs/access.log --error-logfile ${workDir}/logs/error.log --log-level info rtutils.wsgi:application'";

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
                          # RT_TOKEN and LDAP settings are intentionally NOT
                          # injected here from Nix options so they can remain
                          # in the external `secretsFile` (sops) and sourced at
                          # runtime. The service `preStart` step already sources
                          # `${secretEnvFile}` and the optional `secretsFile`.
                          "PYTHONPATH=${pythonPath}"
                        ]
                        ++ lib.optional (
                          config.services.requestTrackerUtils.ldapCaCertFile != null
                        ) "LDAP_CA_CERT_FILE=${config.services.requestTrackerUtils.ldapCaCertFile}";
                        Restart = "always";
                        RestartSec = "10s";
                        User = config.services.requestTrackerUtils.user;
                        Group = config.services.requestTrackerUtils.group;

                        NoNewPrivileges = true;
                        PrivateTmp = true;
                        ProtectSystem = "strict";
                        ProtectHome = true;
                        ReadWritePaths = [ config.services.requestTrackerUtils.workingDirectory ];
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
