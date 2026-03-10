package auth

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"time"

	"hire_sense/database"

	"github.com/golang-jwt/jwt/v5"
	"github.com/google/uuid"
)

type Claims struct {
	Role string `json:"role"`
	jwt.RegisteredClaims
}

type TokenManager struct {
	privateKey any
	publicKey  any
	issuer     string
	ttl        time.Duration
}

type IssuedToken struct {
	Raw       string
	TokenID   string
	ExpiresAt time.Time
}

func NewTokenManager(issuer string, ttl time.Duration) (*TokenManager, error) {
	privateKey, err := jwt.ParseRSAPrivateKeyFromPEM(embeddedPrivateKeyPEM)
	if err != nil {
		return nil, fmt.Errorf("parse private key: %w", err)
	}
	publicKey, err := jwt.ParseRSAPublicKeyFromPEM(embeddedPublicKeyPEM)
	if err != nil {
		return nil, fmt.Errorf("parse public key: %w", err)
	}

	return &TokenManager{
		privateKey: privateKey,
		publicKey:  publicKey,
		issuer:     issuer,
		ttl:        ttl,
	}, nil
}

func (m *TokenManager) IssueToken(user database.User) (IssuedToken, error) {
	now := time.Now().UTC()
	tokenID := uuid.NewString()

	claims := Claims{
		Role: string(user.Role),
		RegisteredClaims: jwt.RegisteredClaims{
			Issuer:    m.issuer,
			Subject:   user.ID,
			ID:        tokenID,
			IssuedAt:  jwt.NewNumericDate(now),
			NotBefore: jwt.NewNumericDate(now),
			ExpiresAt: jwt.NewNumericDate(now.Add(m.ttl)),
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodRS256, claims)
	raw, err := token.SignedString(m.privateKey)
	if err != nil {
		return IssuedToken{}, fmt.Errorf("sign token: %w", err)
	}

	return IssuedToken{
		Raw:       raw,
		TokenID:   tokenID,
		ExpiresAt: now.Add(m.ttl),
	}, nil
}

func (m *TokenManager) ParseToken(raw string) (*Claims, error) {
	token, err := jwt.ParseWithClaims(
		raw,
		&Claims{},
		func(token *jwt.Token) (any, error) {
			return m.publicKey, nil
		},
		jwt.WithIssuer(m.issuer),
		jwt.WithExpirationRequired(),
		jwt.WithValidMethods([]string{jwt.SigningMethodRS256.Alg()}),
	)
	if err != nil {
		return nil, err
	}

	claims, ok := token.Claims.(*Claims)
	if !ok || !token.Valid {
		return nil, fmt.Errorf("invalid token claims")
	}

	return claims, nil
}

func HashToken(raw string) string {
	sum := sha256.Sum256([]byte(raw))
	return hex.EncodeToString(sum[:])
}
