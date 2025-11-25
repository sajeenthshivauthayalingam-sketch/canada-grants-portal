from youreka import create_app

# You can switch to ProdConfig via env var if needed.
app = create_app("DevConfig")

if __name__ == "__main__":
    app.run()
