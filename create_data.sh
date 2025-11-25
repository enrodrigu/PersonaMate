#!/bin/bash

# Create the directory if it doesn't exist
mkdir -p data
PERSONAL_DATA=data/personal_data.json

# If the file does not exist or is empty, write an empty JSON array so it's valid JSON
if [ ! -s "$PERSONAL_DATA" ]; then
	echo "[]" > "$PERSONAL_DATA"
	echo "Created $PERSONAL_DATA with empty JSON array"
else
	echo "$PERSONAL_DATA already exists and is non-empty"
fi