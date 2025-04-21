# StudyAI Web Deployment

This repository contains the web version of StudyAI, a platform for creating AI study assistants trained on your personal study materials.

## Features

- User authentication system
- Upload and process study materials
- AI-powered question answering
- Automatic flashcard generation
- Quiz creation and scoring
- Responsive web interface

## Deployment Instructions

### Prerequisites

- Python 3.10+
- PostgreSQL database (for production)
- Hugging Face API token

### Environment Variables

Set the following environment variables:

```
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://username:password@host:port/database
HUGGINGFACEHUB_API_TOKEN=your-huggingface-token
```

### Local Development

1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run the application: `python run.py`

### Deployment to Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn run:app`
4. Add the environment variables listed above
5. Deploy the application

## Project Structure

```
web_version/
├── app/
│   ├── models/
│   │   └── models.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── forms.py
│   │   ├── main.py
│   │   └── study.py
│   ├── static/
│   │   ├── css/
│   │   └── js/
│   ├── templates/
│   │   ├── auth/
│   │   ├── main/
│   │   └── study/
│   ├── uploads/
│   ├── utils/
│   │   ├── auth_helpers.py
│   │   ├── auth_routes.py
│   │   └── document_processor.py
│   └── __init__.py
├── config.py
├── Procfile
├── requirements.txt
├── run.py
└── runtime.txt
```

## License

This project is open-source and free to use, modify, and distribute.
