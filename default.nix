{ pkgs ? import <nixpkgs> {}, lib ? pkgs.lib }:
{
  shell = pkgs.mkShell {
    buildInputs = [
      (pkgs.python3.withPackages (ps: [
        ps.taskw
        ps.caldav
        ps.keyring
        ps.click
        ps.secretstorage
        ps.dbus-python
        ps.pydantic
        ps.pydantic-settings
        (ps.callPackage ./nix/cpmpy.nix { })
      ]))
    ];
  };
}
