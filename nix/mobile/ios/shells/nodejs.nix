{ mkShell, nodejs, deps }:

mkShell {
  shellHook = ''
    # Fix for ERR_OSSL_EVP_UNSUPPORTED error.
    export NODE_OPTIONS="--openssl-legacy-provider";
    # Same fix but for Xcode React Native script.
    export NODE_ARGS="--openssl-legacy-provider --max-old-space-size=16384";
    # Fix Xcode using system Node.js version.
    export NODE_BINARY="${nodejs}/bin/node";

    # Check if node modules changed and if so install them.
    "$STATUS_MOBILE_HOME/nix/scripts/node_modules.sh" ${deps.nodejs-patched}
  '';
}
