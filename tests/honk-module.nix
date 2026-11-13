{ self, nixpkgs, pkgs, system }:
let
  evaluate = settings: (nixpkgs.lib.nixosSystem {
    inherit system;
    modules = [
      self.nixosModules.honk
      { services.honk-proxy = { enable = true; } // settings; }
    ];
  }).config;
  normal = evaluate {};
  manual = evaluate { startAtBoot = false; initialConfig = null; };
  service = normal.systemd.services.honk-core;
in
assert service.wantedBy == [ "multi-user.target" ];
assert manual.systemd.services.honk-core.wantedBy == [];
assert service.serviceConfig.StateDirectory == "honk";
assert builtins.elem "dae.service" service.conflicts;
assert nixpkgs.lib.hasInfix "/bin/honk-core --config" service.serviceConfig.ExecStart;
pkgs.runCommand "honk-module-check" {} ''
  # Force complete unit rendering, including the nullable seed configuration.
  test -s ${pkgs.writeText "honk-auto.service" normal.systemd.units."honk-core.service".text}
  test -s ${pkgs.writeText "honk-manual.service" manual.systemd.units."honk-core.service".text}
  touch "$out"
''
