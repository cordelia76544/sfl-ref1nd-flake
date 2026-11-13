self:
{ config, lib, pkgs, ... }:
let
  cfg = config.services.honk-proxy;
  initial = pkgs.writeText "honk-initial.dae" cfg.initialConfig;
in {
  options.services.honk-proxy = {
    enable = lib.mkEnableOption "honk with the embedded doona web interface";
    package = lib.mkOption {
      type = lib.types.package;
      default = self.packages.${pkgs.stdenv.hostPlatform.system}.honk;
      description = "The honk package to run.";
    };
    startAtBoot = lib.mkOption {
      type = lib.types.bool;
      default = true;
      description = "Start honk at boot; disable for manual systemctl start honk-core.";
    };
    configFile = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/honk/config.dae";
      description = "Absolute writable configuration path outside the Nix store.";
    };
    initialConfig = lib.mkOption {
      type = lib.types.nullOr lib.types.lines;
      default = ''
        global {
            wan_interface: auto
            data_dir: '/var/lib/honk'
            log_level: info
            auto_config_kernel_parameter: true
            bootstrap_resolver: '223.5.5.5:53'
        }
        routing {
            fallback: direct
        }
        experimental {
            native_api {
                enabled: true
                listen: '127.0.0.1:9527'
                password_auth: true
                config_write: true
                ui: 'embedded'
            }
        }
      '';
      description = ''
        Seed configuration, copied only when configFile does not exist.
        Later web edits survive rebuilds. Set null to manage the file yourself.
        This text is stored in the world-readable Nix store: do not put secrets here.
        Keep global.data_dir at /var/lib/honk for the module's state directory.
      '';
    };
  };
  config = lib.mkIf cfg.enable {
    assertions = [{
      assertion = lib.hasPrefix "/" cfg.configFile && !(lib.hasPrefix builtins.storeDir cfg.configFile);
      message = "services.honk-proxy.configFile must be an absolute path outside the Nix store.";
    }];
    environment.systemPackages = [ cfg.package ];
    systemd.services.honk-core = {
      description = "honk proxy with embedded doona Web UI";
      wantedBy = lib.optional cfg.startAtBoot "multi-user.target";
      wants = [ "network-online.target" ];
      after = [ "network-online.target" "systemd-sysctl.service" "systemd-modules-load.service" "dae.service" ];
      conflicts = [ "dae.service" ];
      environment.SSL_CERT_FILE = "${pkgs.cacert}/etc/ssl/certs/ca-bundle.crt";
      preStart = ''
        install -d -m0700 /var/lib/honk/config.d
      '' + lib.optionalString (cfg.initialConfig != null) ''
        if [ ! -e ${lib.escapeShellArg cfg.configFile} ]; then
          install -Dm0600 ${initial} ${lib.escapeShellArg cfg.configFile}
        fi
      '';
      serviceConfig = {
        Type = "notify";
        User = "root";
        StateDirectory = "honk";
        StateDirectoryMode = "0700";
        WorkingDirectory = "/var/lib/honk";
        UMask = "0077";
        ExecStart = "${lib.getExe cfg.package} --config ${lib.escapeShellArg cfg.configFile} --disable-timestamp";
        ExecReload = "${lib.getExe cfg.package} reload";
        Restart = "on-failure";
        RestartSec = "2s";
        TimeoutStartSec = "120s";
        TimeoutStopSec = "30s";
        LimitNOFILE = 1048576;
        LimitMEMLOCK = "infinity";
      };
      unitConfig.StartLimitIntervalSec = 0;
    };
  };
}
