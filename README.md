# IEI Sequencing Platform MVP

A bioinformatics web application for analyzing genetic variants in patients with
Inborn Errors of Immunity (IEI).

## Stack

- **Backend**: Python 3.11+, Django 5, Django REST Framework, Celery + Redis
- **Frontend**: React 18 (Vite), TanStack Query, TanStack Table, Tailwind CSS
- **Database**: PostgreSQL 16
- **Bioinformatics**: Biopython, pure-Python pipeline fallbacks

## Quick start

```bash
# 1. Start infrastructure
docker-compose up -d

# 2. Set up backend
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Visit http://localhost:8000/admin/
