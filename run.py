from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, extra_files=None, exclude_patterns=['*.pyc'])
