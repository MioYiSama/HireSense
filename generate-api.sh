openapi-generator-cli generate -i ./backend/openapi.yml -g typescript-axios -o ./frontend/src/api
rm -rf ./frontend/src/api/docs