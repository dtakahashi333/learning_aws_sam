# Use the below command to run the container to be persistent.
# docker run -d -p 8000:8000 \
#   --name dynamodb-local \
#   -v ~/dynamodb-data:/app/dynamodb_local/data \
#   dynamodb-python-local \
#   java -Djava.library.path=./dynamodb_local/DynamoDBLocal_lib \
#        -jar ./dynamodb_local/DynamoDBLocal.jar \
#        -sharedDb \
#        -dbPath ./dynamodb_local/data \
#        -port 8000

# Use official Python base image
FROM python:3.13-slim

# Install Java (required by DynamoDB Local)
RUN apt-get update && \
    apt-get install -y openjdk-17-jre-headless wget unzip && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Download DynamoDB Local
RUN wget https://s3.us-west-2.amazonaws.com/dynamodb-local/dynamodb_local_latest.zip -O dynamodb_local.zip && \
    unzip dynamodb_local.zip -d dynamodb_local && \
    rm dynamodb_local.zip

# Install Python dependencies (boto3 for DynamoDB)
RUN pip install --no-cache-dir boto3

# Expose DynamoDB port
EXPOSE 8000

# Default command: run DynamoDB Local
CMD ["java", "-Djava.library.path=./dynamodb_local/DynamoDBLocal_lib", "-jar", "./dynamodb_local/DynamoDBLocal.jar", "-sharedDb", "-dbPath", "./dynamodb_local/data", "-port", "8000"]