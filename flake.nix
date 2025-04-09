{
  description = "Nix flake for a Flask app with a NixOS service module";

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
    let
      pkgs = import nixpkgs { system = "x86_64-linux"; }; # Import pkgs
      lib = pkgs.lib; # Use lib from pkgs
    in
    {
      # Define the NixOS module at the top level
      nixosModules.requestTrackerUtils =
        {
          config,
          lib,
          pkgs,
          ...
        }:
        {
          options.requestTrackerUtils = {
            enable = lib.mkOption {
              type = lib.types.bool;
              default = false;
              description = "Enable the Flask app service.";
            };
            host = lib.mkOption {
              type = lib.types.str;
              default = "127.0.0.1";
              description = "Host address for the Flask app.";
            };
            port = lib.mkOption {
              type = lib.types.int;
              default = 5000;
              description = "Port for the Flask app.";
            };
            secretsFile = lib.mkOption {
              type = lib.types.path;
              default = "/etc/request-tracker-utils/secrets.env";
              description = "Path to the secrets environment file.";
            };
            workingDirectory = lib.mkOption {
              type = lib.types.str;
              default = "/var/lib/request-tracker-utils";
              description = "Working directory for the Flask app service.";
            };
            user = lib.mkOption {
              type = lib.types.str;
              default = "rtutils";
              description = "User to run the Flask app service as.";
            };
            group = lib.mkOption {
              type = lib.types.str;
              default = "rtutils";
              description = "Group to run the Flask app service as.";
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
          };

          config = lib.mkIf config.requestTrackerUtils.enable {
            # Systemd service definition
            systemd.services.request-tracker-utils = {
              description = "Flask app service";
              after = [ "network.target" ];
              wantedBy = [ "multi-user.target" ];
              serviceConfig = {
                ExecStart = "${pkgs.python3}/bin/python3 -m app";
                WorkingDirectory = config.requestTrackerUtils.workingDirectory;
                Environment = lib.mkMerge [
                  "FLASK_APP=app"
                  "WORKING_DIR=${config.requestTrackerUtils.workingDirectory}"
                  "LABEL_WIDTH_MM=${toString config.requestTrackerUtils.labelWidthMm}"
                  "LABEL_HEIGHT_MM=${toString config.requestTrackerUtils.labelHeightMm}"
                  "RT_URL=${config.requestTrackerUtils.rtUrl}"
                  "API_ENDPOINT=${config.requestTrackerUtils.apiEndpoint}"
                  "PREFIX=${config.requestTrackerUtils.prefix}"
                  "PADDING=${toString config.requestTrackerUtils.padding}"
                ];
                EnvironmentFile = config.requestTrackerUtils.secretsFile; # Use the secretsFile option
                Restart = "always";
                User = config.requestTrackerUtils.user;
                Group = config.requestTrackerUtils.group;
              };
            };

            # Ensure the user and group exist
            users.users.${config.requestTrackerUtils.user} = {
              isSystemUser = true;
              group = config.requestTrackerUtils.group;
            };

            users.groups.${config.requestTrackerUtils.group} = { };

            # Create the working directory
            system.activationScripts.create-request-tracker-utils-dir = lib.mkAfter ''
              mkdir -p ${config.requestTrackerUtils.workingDirectory}
              chown ${config.requestTrackerUtils.user}:${config.requestTrackerUtils.group} ${config.requestTrackerUtils.workingDirectory}
            '';
          };
        };

      # Package definition for the Flask app
      packages.default = pkgs.python3Packages.buildPythonApplication {
        pname = "request-tracker-utils";
        version = "0.3.0";

        # Path to your Flask app source code
        src = ./.;

        # Use pyproject.toml for building
        format = "pyproject";

        # Python dependencies
        propagatedBuildInputs = with pkgs.python3Packages; [
          pandas
          requests
          flask
          click
          reportlab
          qrcode
          python-barcode
          python-dotenv
        ];

        # Entry point for the Flask app
        postInstall = ''
          mkdir -p $out/bin
          echo '#!/bin/sh' > $out/bin/request-tracker-utils
          echo 'exec ${pkgs.python3}/bin/python3 -m app' >> $out/bin/request-tracker-utils
          chmod +x $out/bin/request-tracker-utils
        '';

        meta = with pkgs.lib; {
          description = "Flask app for Request Tracker";
          license = lib.licenses.mit;
          maintainers = [ lib.maintainers.jmartinWestern ];
        };
      };
    };
}
