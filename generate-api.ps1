openapi-generator-cli generate -i .\backend\openapi.yml -g typescript-axios -o .\frontend\src\api
Remove-Item .\frontend\src\api\docs -Recurse -Force