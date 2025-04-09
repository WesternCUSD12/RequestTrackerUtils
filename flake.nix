{
  description = "Nix flake for a Flask app with a NixOS service module";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs { inherit system; };
      lib = pkgs.lib; # Define lib from pkgs
      isNixos = pkgs.stdenv.isLinux; # Check if the system is Linux
    in {
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
          echo 'exec python3 -m app' >> $out/bin/request-tracker-utils
          chmod +x $out/bin/request-tracker-utils
        '';

        meta = with pkgs.lib; {
          description = "Flask app for Request Tracker";
          license = licenses.mit;
          maintainers = [ maintainers.jmartinWestern ];
        };
      };

      # NixOS module for the Flask app service (only for Linux systems)
      nixosModules = lib.optionalAttrs isNixos {
        requestTrackerUtils = {
          config, lib, pkgs, ... }: {
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
            };

            config = lib.mkIf config.requestTrackerUtils.enable {
              # Systemd service definition
              systemd.services.request-tracker-utils = {
                description = "Flask app service";
                after = [ "network.target" ];
                wantedBy = [ "multi-user.target" ];
                serviceConfig = {
                  ExecStart = "${pkgs.python3}/bin/python3 -m app";
                  WorkingDirectory = "/var/lib/request-tracker-utils";
                  Environment = "FLASK_APP=app";
                  EnvironmentFile = config.requestTrackerUtils.secretsFile; # Use the secretsFile option
                  Restart = "always";
                  User = "rtutils";
                  Group = "rtutils";
                };
              };

              # Ensure the user and group exist
              users.users.rtutils = {
                isSystemUser = true;
                group = "rtutils";
              };

              users.groups.rtutils = {};
            };
          };
      };
    });
}