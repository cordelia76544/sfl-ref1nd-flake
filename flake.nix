{
  description = "reF1nd SFL and honk with embedded doona for NixOS";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  outputs = { self, nixpkgs }: let
    systems = [ "x86_64-linux" "aarch64-linux" ];
    each = nixpkgs.lib.genAttrs systems;
  in {
    packages = each (system: let pkgs = import nixpkgs { inherit system; }; in rec {
      sfl = pkgs.callPackage ./package.nix {};
      honk = pkgs.callPackage ./honk/package.nix {};
      default = sfl;
    });
    checks = each (system: let
      pkgs = import nixpkgs { inherit system; };
    in {
      package = self.packages.${system}.default;
      honk = self.packages.${system}.honk;
      honk-module = import ./tests/honk-module.nix { inherit self nixpkgs pkgs system; };
    });
    nixosModules.honk = import ./honk/module.nix self;
    nixosModules.default = { config, lib, pkgs, ... }: let
      cfg = config.programs.sfl-ref1nd;
    in {
      options.programs.sfl-ref1nd = {
        enable = lib.mkEnableOption "reF1nd SFL and its privileged daemon";
        package = lib.mkOption {
          type = lib.types.package;
          default = self.packages.${pkgs.stdenv.hostPlatform.system}.default;
        };
      };
      config = lib.mkIf cfg.enable {
        environment.systemPackages = [ cfg.package ];
        security.polkit.enable = true;
        systemd.packages = [ cfg.package ];
        systemd.services.sing-box-daemon-reF1nd.wantedBy = [ "multi-user.target" ];
      };
    };
  };
}

