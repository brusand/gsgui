#!/bin/sh
# Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).
mkdir -p dist/dmg
# Empty the dmg folder.
rm -r dist/dmg/*
# Copy the app bundle to the dmg folder.
cp -r "dist/gsgui.app" dist/dmg
# If the DMG already exists, delete it.
test -f "dist/gsgui.dmg" && rm "dist/gsgui.dmg"
create-dmg \
  --volname "GsGui" \
  --window-pos 200 120 \
  --window-size 800 600 \
  --icon-size 128 \
  --hide-extension "gsgui.app" \
  --app-drop-link 425 120 \
  "dist/GsGui.dmg" \
  "dist/dmg/"

