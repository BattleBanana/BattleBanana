FROM python:3.10-slim

WORKDIR /usr/src/app

# ensure local python is preferred over distribution python
ENV PATH /usr/local/bin:$PATH

# Install ssdeep requirements
RUN apt-get update
RUN apt-get install -y build-essential libffi-dev libfuzzy-dev libfuzzy2 libffi-dev automake autoconf libtool git

# Copy requirements file to container & Install the requirements
COPY requirements.txt .
RUN python3.10 -m pip install -r requirements.txt

# Copy the app to the container
COPY . .

# Run setup.py in helpers/ directory and clean up unneeded files
RUN cd dueutil/game/helpers/ \
    && python3.10 setup.py build_ext --inplace \
    && cd ~

RUN rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Run the app
CMD ["python3.10", "run.py"]
