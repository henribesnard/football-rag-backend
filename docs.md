# Alembic 
# Naviguer dans le dossier alembic 
# générer migration 
alembic revision --autogenerate -m "Initial migration"
# Migrer 
alembic upgrade head
