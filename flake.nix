{
  description = "Development environment for Katalogas (data.gov.lt)";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      system = "x86_64-linux";
      pkgs = nixpkgs.legacyPackages.${system};

      # Shared across buildInputs and LD_LIBRARY_PATH
      libs = with pkgs; [
        stdenv.cc.cc.lib
        glib
        gobject-introspection
        cairo
        pango
        gdk-pixbuf
        harfbuzz
        freetype
        fontconfig
        libjpeg
        libpng
        libxml2
        libxslt
        zlib
        libffi
        openssl
        geos
        proj
        gdal
      ];
    in {
      devShells.${system}.default = pkgs.mkShell {
        buildInputs = with pkgs; [
          python311
          poetry
          nodejs

          # Rust toolchain (for building native extensions)
          cargo
          rustc

          # GitHub CLI
          gh

          # C build tools
          pkg-config
          gcc
        ] ++ libs;

        shellHook = ''
          if [ ! -f .env ]; then
            cp .env.example .env
          fi
          set -a
          source .env
          set +a

          export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath libs}''${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

          poetry env use ${pkgs.python311}/bin/python
          export PATH="$(poetry env info -p)/bin:$PATH"

          echo "=== Dev environment ready ==="
          echo "Python: $(python3 --version)"
          echo "Poetry: $(poetry --version)"
          echo "Node:   $(node --version)"
          echo "Docker: $(docker --version 2>/dev/null || echo 'not running')"
        '';
      };
    };
}
