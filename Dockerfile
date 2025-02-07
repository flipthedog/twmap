FROM public.ecr.aws/docker/library/python:3.10-bullseye

# Install Poetry
RUN pip install poetry

# Copy the pyproject.toml and poetry.lock files into the container
COPY pyproject.toml poetry.lock /usr/src/app/

# Install the Python dependencies using Poetry
WORKDIR /usr/src/app
RUN poetry install --no-root

# Copy the entire project directory into the container
COPY . /usr/src/app

# Set the working directory
WORKDIR /usr/src/app

ENV PYTHONPATH=/usr/src/app

# Run main.py
CMD ["poetry", "run", "python", "twmap/main.py"]
