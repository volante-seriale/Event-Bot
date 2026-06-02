# Use a slim version of Python for a smaller image size
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (tzdata is essential for zoneinfo)
RUN apt-get update && apt-get install -y tzdata && rm -rf /var/lib/apt/lists/*

# Copy requirements and install them
# (Create a requirements.txt with: discord.py, python-dotenv, tzdata)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot code
COPY . .

# Run the bot
CMD ["python", "bot.py"]