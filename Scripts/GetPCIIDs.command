#!/usr/bin/env bash

# Get the curent directory
dir="$(cd -- "$(dirname "$0")" >/dev/null 2>&1; pwd -P)"
echo Resolving download URL...
base="https://pci-ids.ucw.cz"
suffix="$(curl -s "$base" | grep -i ">pci.ids.gz</a>" | cut -d\" -f2)"
if [ -z "$suffix" ]; then
    echo "Failed to resolve URL"
    exit 1
fi
url="$base$suffix"
echo "Got: $url"
echo "Downloading..."
curl -compressed "$url" -o "$dir/pci.ids.gz"
if [ ! -e "$dir/pci.ids.gz" ]; then
    echo "Failed to download"
    exit 1
fi
echo "Decompressing..."
gunzip -f "$dir/pci.ids.gz"
if [ "$?" != "0" ]; then
    echo "Failed to decompress"
    exit 1
fi
echo
echo "Done"