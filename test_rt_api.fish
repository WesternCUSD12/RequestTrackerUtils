#!/usr/bin/env fish
# Test RT API calls to explore custom field values

# Get RT_TOKEN from environment
set RT_TOKEN (printenv RT_TOKEN)
set RT_URL "https://tickets.wc-12.com/REST/2.0"

if test -z "$RT_TOKEN"
    echo "Error: RT_TOKEN not set"
    exit 1
end

echo "=== Testing RT API Custom Fields ==="
echo ""

# Test 1: Get Manufacturer custom field (ID 9) details
echo "1. Getting Manufacturer field details (ID 9):"
curl -s -H "Authorization: token $RT_TOKEN" \
     "$RT_URL/customfield/9" | jq '.'
echo ""
echo "---"
echo ""

# Test 2: Get Model custom field (ID 4) details
echo "2. Getting Model field details (ID 4):"
curl -s -H "Authorization: token $RT_TOKEN" \
     "$RT_URL/customfield/4" | jq '.'
echo ""
echo "---"
echo ""

# Test 3: Search for all custom fields with Type=Select or Type=Combobox
echo "3. Searching for Select/Combobox custom fields:"
curl -s -H "Authorization: token $RT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '[{"field":"Type","operator":"=","value":"Select"}]' \
     "$RT_URL/customfields" | jq '.items | length'
echo ""
echo "---"
echo ""

# Test 4: Get all custom fields (no filter)
echo "4. Getting all custom fields:"
curl -s -H "Authorization: token $RT_TOKEN" \
     -H "Content-Type: application/json" \
     -X POST \
     -d '[]' \
     "$RT_URL/customfields" | jq '.items | map({id, _url})'
echo ""
echo "---"
echo ""

# Test 5: Get Manufacturer field with explicit category (if applicable)
echo "5. Getting Manufacturer field with possible category filter:"
curl -s -H "Authorization: token $RT_TOKEN" \
     "$RT_URL/customfield/9?category=assets" | jq '.'
echo ""
