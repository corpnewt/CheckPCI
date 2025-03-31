#!/usr/bin/env bash

# Get the curent directory
dir="$(cd -- "$(dirname "$0")" >/dev/null 2>&1; pwd -P)"
echo Resolving download URL...
base="https://pci-ids.ucw.cz"
suffix="$(curl -s "$base" | grep -i ">pci.ids</a>" | cut -d\" -f2)"
if [ -z "$suffix" ]; then
    echo "Failed to resolve URL"
    exit 1
fi
url="$base$suffix"
echo "Got: $url"
echo "Downloading..."
curl "$url" -o "$dir/pci.ids"
echo
if [ -e "$dir/pci.ids" ]; then
    echo "Saved to: $dir/pci.ids"
else
    echo "Failed to download"
    exit 1
fi