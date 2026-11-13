# SFL reF1nd and honk for NixOS

Packages the upstream **Linux GUI**, including its bundled daemon, from the stable
[reF1nd releases](https://github.com/reF1nd/sing-box-releases/releases).
Supports `x86_64-linux` and `aarch64-linux`. No Electron compilation is required.

Also packages the official static musl **honk full** release, including its
embedded **doona and doona lite**. SFL remains the default package and module.
Neither package requires a private binary cache or Cachix account.

## honk + doona

Use the same `sfl-ref1nd` flake input shown below, and add
`inputs.sfl-ref1nd.nixosModules.honk` to your NixOS modules. Enable:

```nix
services.honk-proxy = {
  enable = true;
  startAtBoot = false; # omit or set true to start at boot
};
```

After rebuilding, run `sudo systemctl start honk-core`, then open
<http://127.0.0.1:9527/ui/> and create the administrator account.
The first start seeds a direct-only, host-traffic configuration with the native
API, password authentication and configuration editing enabled. Add subscriptions
and routing through doona. The module does not open firewall ports.

Configuration is `/var/lib/honk/config.dae`; accounts and state also live under
`/var/lib/honk`. Persist the whole directory on ephemeral systems. The seed is
copied only when the configuration does not exist, so web edits survive rebuilds
and changes to `initialConfig` do not overwrite existing files. To use doona lite,
change the native API's `ui` setting to `'embedded-lite'` and restart.

You may supply `services.honk-proxy.initialConfig` for initial setup (no secrets:
it enters the Nix store), or set it to `null` and provision the writable config
yourself. `configFile` selects another absolute path outside the Nix store; keep
`global.data_dir` at `/var/lib/honk` when using this module.

When migrating from a custom `svc/honk.nix`, replace its import with this module
instead of enabling both definitions. Existing `/var/lib/honk/config.dae` and
included `config.d/*.dae` files are preserved. Existing configurations must
already enable the native API and embedded UI, or be edited to do so. The service
name remains `honk-core.service`. Stop SFL's TUN mode before starting honk; honk
also declares a conflict with `dae.service`. Linux 6.12+, the upstream kernel
features and mounted bpffs are required; see the
[honk startup guide](https://github.com/daeuniverse/honk/blob/main/doc/en/how-to-start.md).

Package-only usage (does not enable a system service):

```sh
nix build .#honk
./result/bin/honk-core --version
```

The `honk` binary name is also available as an alias of `honk-core`.

### honk updates

`Update honk and paired doona` checks daily at **10:53 Asia/Shanghai** (02:53 UTC,
subject to GitHub scheduling delays) and supports manual runs. It selects the
highest versioned honk release, including alpha/beta/rc, excluding rolling Debug
and diagnostic tags. It requires both musl `full` assets and their SHA256 digests,
and records the bundled doona version from that honk tag's `pins.env`. Doona is
updated with honk, never independently to a potentially incompatible release.

Both architectures must build and serve **both embedded UIs and their JavaScript
bundles in unprivileged mock mode** before the updater commits `honk/sources.json`.
The NixOS service module is also evaluated. Missing assets or failed checks leave
the previous version in place. These checks do not test real eBPF attachment,
transparent routing or your host configuration. The SFL and honk update workflows
serialize publication; a concurrent manual push can reject the update safely.

The workflow uses the existing `GITHUB_TOKEN`; no extra secret, Cachix setup or
source compilation is needed. It downloads official binaries and retains their
license notices. After a repository update, update your local flake lock and
rebuild as described below. No running machine is upgraded by CI.

To validate honk locally:

```sh
python3 -m unittest discover -s tests
python3 scripts/update-honk.py
nix build .#honk
python3 scripts/check-honk.py ./result/bin/honk-core
```

## NixOS

Add to your system flake inputs:

```nix
sfl-ref1nd.url = "github:cordelia76544/sfl-ref1nd-flake";
# Optional: use your own nixpkgs (compatibility depends on that revision).
# sfl-ref1nd.inputs.nixpkgs.follows = "nixpkgs";
```

Include `inputs.sfl-ref1nd.nixosModules.default` in your NixOS `modules` list,
then enable:

```nix
programs.sfl-ref1nd.enable = true;
```

Rebuild your system, then launch **sing-box-reF1nd** from the application menu.
The module installs the upstream Polkit policy and starts
`sing-box-daemon-reF1nd.service`. An authentication agent must be running in your
desktop session for privileged prompts. It does not add passwordless rules.
GUI configuration and subscriptions are managed inside SFL.
Stop other proxy clients' TUN modes before enabling SFL's TUN.

Daemon data: `/var/lib/sing-box-daemon-reF1nd` (persist this on ephemeral systems).
The GUI keeps user data under your XDG configuration directory; persist its
`sing-box-reF1nd` directory if your home is ephemeral.

```sh
systemctl status sing-box-daemon-reF1nd
journalctl -u sing-box-daemon-reF1nd -b
```

## Updates

The `Update stable SFL` workflow checks at **10:23 Asia/Shanghai** daily (02:23 UTC;
GitHub scheduling may be delayed), or manually via Actions → Run workflow.
It fetches the latest non-prerelease release, requires both DEB assets and their
SHA256 digests, builds on native x86_64 and ARM64 runners, and commits the updated
`sources.json` and lock file only after both builds pass. Missing assets, missing
hashes or build failures leave the published version unchanged.

The default branch must permit the workflow's `GITHUB_TOKEN` to push. Branch
protection can prevent automatic commits. No PAT is needed for an unrestricted
personal repository. Update commits made by `GITHUB_TOKEN` do not retrigger CI;
they have already passed the update workflow's build jobs.

This updates the package repository, **not your running NixOS system**. On your
computer, run from the system flake directory:

```sh
nix flake update sfl-ref1nd
sudo nixos-rebuild switch --flake .#nixos
```

Change `nixos` to your configuration name. The updater preserves the locked
nixpkgs revision; update it separately with `nix flake update nixpkgs` and run CI.

## Development

```sh
python3 scripts/update.py
nix flake check --print-build-logs
nix build
```

`nix run` opens the GUI but does not install/start the privileged daemon; use the
NixOS module for normal operation. Builds verify ELF dependencies and daemon CLI
startup. They do not verify interactive GUI, Polkit authentication or live TUN
routing on your machine. Electron's sandbox is not disabled by this package.
Upstream software retains its original license.

