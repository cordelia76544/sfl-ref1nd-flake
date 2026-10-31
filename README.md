# SFL reF1nd for NixOS

Packages the upstream **Linux GUI**, including its bundled daemon, from the stable
[reF1nd releases](https://github.com/reF1nd/sing-box-releases/releases).
Supports `x86_64-linux` and `aarch64-linux`. No Electron compilation is required.

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
