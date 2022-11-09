FROM python:3.10-slim

WORKDIR /usr/src/app

# Install dependencies for ssdeep
RUN apt-get update && apt-get install -y build-essential libfuzzy-dev

# Copy the app to the container and builded speedups
COPY . .

# Copy requirements file to container & Install the requirements
RUN python3.10 -m pip install -r requirements.txt

# Run setup.py in helpers/ directory and clean up unneeded files
RUN cd dueutil/game/helpers/ \
    && python3.10 setup.py build_ext --inplace \
    && cd ~

CMD ["python3.10", "run.py"]
