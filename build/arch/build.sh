#!/usr/bin/bash

cd ./pkg

# Create parent directories
mkdir -p opt
mkdir usr

# Copy source files
cp -r ../../../safeeyes/share ./usr/
cp -r ../../../safeeyes/safeeyes ./opt/

# # Create the package
# tar -cf - .PKGINFO * | xz -c -z - > ../safeeyes.pkg.tar.xz

# # Remove the copied files
# rm -r ./opt
# rm -r ./usr