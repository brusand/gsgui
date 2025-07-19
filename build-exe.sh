#!/bin/sh
# Create a folder (named dmg) to prepare our DMG in (if it doesn't already exist).
mkdir -p dist/exe
# Empty the dmg folder.
rm -r dist/exe/*
# Copy the app bundle to the dmg folder.
cp -r "dist/gsgui.app" dist/exe
# If the DMG already exists, delete it.
test -f "dist/gsgui.exe" && rm "dist/gsgui.exe"
create-exe\
  --volname "GsGui" \
  --window-pos 200 120 \
  --window-size 600 300 \
  --icon-size 128 \
  --hide-extension "gsgui.app" \
  --app-drop-link 425 120 \
  "dist/GsGui.exe" \
  "dist/exe/"

