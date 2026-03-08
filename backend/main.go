package main

import "github.com/gofiber/fiber/v3"

func main() {
	app := fiber.New(fiber.Config{})

	_ = app.Listen(":8080")
}
