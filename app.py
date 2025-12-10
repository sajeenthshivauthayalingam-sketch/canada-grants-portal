from youreka import create_app

app = create_app("ProdConfig")

if __name__ == "__main__":
    # Local dev
    app.run(debug=True)
