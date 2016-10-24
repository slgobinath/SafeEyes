#!/usr/bin/bash

cd ./pkg

# Create parent directories
mkdir -p opt/safeeyes
mkdir usr

# Copy source files
cp -r ../../../safeeyes/share ./usr/
cp -r ../../../safeeyes/safeeyes ./opt/safeeyes/
cp -r ../../../safeeyes/share/applications/safeeyes.desktop ./opt/safeeyes/

# # Create the package
# tar -cf - .PKGINFO * | xz -c -z - > ../safeeyes.pkg.tar.xz

# # Remove the copied files
# rm -r ./opt
# rm -r ./usr