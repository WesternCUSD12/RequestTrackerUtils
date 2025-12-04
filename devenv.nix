{
  pkgs,
  lib,
  config,
  inputs,
  ...
}:
let
  buildInputs = with pkgs; [
    # stdenv.cc.cc
    libuv
    # ruff is a fast Python linter/formatter used in this project
    ruff
    # zlib
  ];
in
{
  env = {
    LD_LIBRARY_PATH = "${with pkgs; lib.makeLibraryPath buildInputs}";
  };

  # git.enable = true;

  packages = with pkgs;[
    ruff
    pyright
    mypy
  ];

  languages.python = {
    enable = true;
    uv = {
      enable = true;
      sync.enable = true;
    };
  };

  enterShell = ''
    source .devenv/state/venv/bin/activate.fish
  '';

  dotenv.enable = true;
}
