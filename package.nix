{ lib, stdenv, fetchurl, dpkg, autoPatchelfHook, makeWrapper,
  alsa-lib, atk, at-spi2-atk, at-spi2-core, cairo, cups, dbus, expat,
  glib, gtk3, libdrm, libgbm, libxkbcommon, nspr, nss, pango,
  libX11, libXcomposite, libXdamage, libXext, libXfixes, libXrandr,
  libxcb, libXScrnSaver, libXtst, wayland, systemd, libnotify,
  libappindicator-gtk3 }:
let info = builtins.fromJSON (builtins.readFile ./sources.json);
in stdenv.mkDerivation {
  pname = "sfl-ref1nd";
  version = info.version;
  src = fetchurl info.sources.${stdenv.hostPlatform.system};
  nativeBuildInputs = [ dpkg autoPatchelfHook makeWrapper ];
  buildInputs = [ alsa-lib atk at-spi2-atk at-spi2-core cairo cups dbus expat
    glib gtk3 libdrm libgbm libxkbcommon nspr nss pango libX11 libXcomposite
    libXdamage libXext libXfixes libXrandr libxcb libXScrnSaver libXtst wayland
    systemd libnotify libappindicator-gtk3 stdenv.cc.cc.lib ];
  unpackPhase = ''dpkg-deb -x "$src" .'';
  dontBuild = true;
  dontStrip = true;
  installPhase = ''
    runHook preInstall
    mkdir -p "$out/lib" "$out/bin"
    cp -r opt/sing-box-reF1nd "$out/lib/sfl"
    cp -r usr/share "$out/share"
    mkdir -p "$out/lib/systemd/system"
    cp usr/lib/systemd/system/sing-box-daemon-reF1nd.service "$out/lib/systemd/system/"
    substituteInPlace "$out/lib/systemd/system/sing-box-daemon-reF1nd.service" \
      --replace-fail /opt/sing-box-reF1nd "$out/lib/sfl"
    for desktop in "$out"/share/applications/*.desktop; do
      substituteInPlace "$desktop" --replace-fail /opt/sing-box-reF1nd/sing-box-reF1nd "$out/bin/sing-box-reF1nd"
    done
    makeWrapper "$out/lib/sfl/sing-box-reF1nd" "$out/bin/sing-box-reF1nd" \
      --prefix PATH : ${lib.makeBinPath [ systemd ]} \
      --prefix LD_LIBRARY_PATH : ${lib.makeLibraryPath [ wayland libappindicator-gtk3 libnotify ]}
    runHook postInstall
  '';
  meta = {
    description = "reF1nd sing-box for Linux graphical client";
    homepage = "https://github.com/reF1nd/sing-box-for-desktop";
    platforms = [ "x86_64-linux" "aarch64-linux" ];
    mainProgram = "sing-box-reF1nd";
  };
}
