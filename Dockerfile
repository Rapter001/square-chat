# Use a specific version of Python for stability
FROM python:latest

# Set the working directory inside the container
WORKDIR /app

# Copy only the requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies with no cache to reduce image size
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files
COPY . .

# Expose the port your application will run on
EXPOSE 5000

# Set the default command to run the application
CMD ["python", "main.py"]