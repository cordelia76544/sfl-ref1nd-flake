{ lib, stdenvNoCC, python3, gtk3, libayatana-appindicator, gobject-introspection,
  wrapGAppsHook3, makeWrapper, systemd, xvfb-run, dbus }:
let python = python3.withPackages (ps: [ ps.pygobject3 ]);
in stdenvNoCC.mkDerivation (finalAttrs: {
  pname = "honk-tray";
  version = "0.1.0";
  src = ./.;
  nativeBuildInputs = [ wrapGAppsHook3 makeWrapper gobject-introspection ];
  buildInputs = [ gtk3 libayatana-appindicator ];
  dontBuild = true;
  installPhase = ''
    mkdir -p "$out/lib/honk-tray" "$out/bin" "$out/share/icons/hicolor/scalable/apps" "$out/share/applications"
    cp *.py "$out/lib/honk-tray/"
    cp icons/*.svg "$out/share/icons/hicolor/scalable/apps/"
    substituteInPlace "$out/lib/honk-tray/tray.py" \
      --replace-fail '@systemctl@' '${systemd}/bin/systemctl' \
      --replace-fail '@journalctl@' '${systemd}/bin/journalctl' \
      --replace-fail '@icons@' "$out/share/icons/hicolor/scalable/apps"
    makeWrapper ${python}/bin/python3 "$out/bin/honk-tray" \
      --add-flags "$out/lib/honk-tray/tray.py"
    cp honk-tray.desktop "$out/share/applications/"
    substituteInPlace "$out/share/applications/honk-tray.desktop" \
      --replace-fail 'Exec=honk-tray' "Exec=$out/bin/honk-tray"
  '';
  passthru.tests.smoke = stdenvNoCC.mkDerivation {
    name = "honk-tray-smoke";
    dontUnpack = true;
    nativeBuildInputs = [ xvfb-run dbus ];
    buildPhase = ''
      export HOME="$TMPDIR/home"
      mkdir -p "$HOME"
      export GDK_BACKEND=x11
      dbus-run-session --config-file=${dbus}/share/dbus-1/session.conf -- \
        xvfb-run -a ${finalAttrs.finalPackage}/bin/honk-tray --self-test
    '';
    installPhase = "touch $out";
  };
  meta = {
    description = "Desktop tray controls for the honk system service";
    mainProgram = "honk-tray";
    platforms = [ "x86_64-linux" "aarch64-linux" ];
  };
})
