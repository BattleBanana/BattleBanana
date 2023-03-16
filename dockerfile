FROM python:3.11-slim

WORKDIR /usr/src/app

# Install dependencies for ssdeep
RUN apt-get update && apt-get install --no-install-recommends -y build-essential libfuzzy-dev

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt

# Copy the app to the container
COPY . .

# Run setup.py in helpers/ directory and clean up unneeded files
RUN cd dueutil/game/helpers/ \
    && python3 setup.py build_ext --inplace \
    && cd ~

CMD ["python3", "run.py"]
