# Use an official Python runtime as the base image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that Chainlit runs on
EXPOSE 8000

# Define the command to run the application
CMD ["chainlit", "run", "autogen.py", "-h", "0.0.0.0", "-p", "8000"]
