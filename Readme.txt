# Cloud Cost Optimizer Dashboard

## Overview
A Dockerized AWS cloud monitoring and cost optimization dashboard built using Streamlit and Boto3.

## Features
- Real-time EC2 monitoring
- Monthly cost estimation
- Running/stopped instance tracking
- Dockerized deployment
- AWS IAM Role integration
- EC2 hosted deployment

## Tech Stack
- Python
- Streamlit
- Boto3
- Docker
- AWS EC2
- IAM Roles

## Deployment Architecture
Local → Docker → Docker Hub → EC2

## Screenshots
![Dashboard](screenshots/dashboard.png)

## Run Locally

docker build -t cloud-cost-optimizer .
docker run -p 8501:8501 cloud-cost-optimizer

## Future Improvements
- Authentication
- CI/CD
- CloudWatch integration
- Cost anomaly alerts