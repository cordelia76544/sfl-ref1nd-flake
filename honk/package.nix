{ lib, stdenvNoCC, fetchurl }:
let
  info = builtins.fromJSON (builtins.readFile ./sources.json);
in stdenvNoCC.mkDerivation {
  pname = "honk";
  inherit (info) version;
  src = fetchurl info.sources.${stdenvNoCC.hostPlatform.system};

  # Upstream's musl full build embeds eBPF, doona and doona lite.
  dontBuild = true;
  dontStrip = true;
  dontPatchELF = true;
  installPhase = ''
    runHook preInstall
    install -Dm755 honk-core "$out/bin/honk-core"
    ln -s honk-core "$out/bin/honk"
    mkdir -p "$out/share/doc/honk"
    cp -r LICENSE README.md doona doona-lite "$out/share/doc/honk/"
    runHook postInstall
  '';
  passthru.doonaVersion = info.doonaVersion;
  meta = {
    description = "honk transparent proxy with embedded doona and doona lite";
    homepage = "https://github.com/daeuniverse/honk";
    license = lib.licenses.gpl3Only;
    platforms = [ "x86_64-linux" "aarch64-linux" ];
    mainProgram = "honk-core";
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
  };
}
