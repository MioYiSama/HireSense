package auth

import _ "embed"

var (
	//go:embed private.pem
	embeddedPrivateKeyPEM []byte

	//go:embed public.pem
	embeddedPublicKeyPEM []byte
)
