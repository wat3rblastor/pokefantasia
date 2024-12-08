# Pokefantasia Serverless Architecture Setup Instructions

This document outlines the steps to set up AWS services for the Pokefantasia project, including Lambda functions, RDS, ECR, and IAM configurations.

---

## Prerequisites

Before proceeding, ensure you have the following:
- AWS CLI installed and configured with your credentials.
- Permissions to create AWS resources like Lambda functions, RDS, and ECR.
- Docker installed for handling ECR-related tasks.

---

## 1. AWS IAM Profile Setup

1. **Navigate to the IAM Console**:
   - Open the AWS Management Console and search for **IAM**.

2. **Create an IAM Role for Lambda**:
   - Go to **Roles** and click **Create role**.
   - Select **AWS Service** and choose **Lambda**.
   - Attach the necessary policies.
   - Name the role (e.g., `LambdaExecutionRole`) and click **Create role**.

3. **Attach the IAM Role to Lambda Functions**:
   - Open the **Lambda Console** and select the desired function.
   - Navigate to the **Configuration** tab.
   - Under **Execution role**, attach the IAM role created in the previous step.

---

## 2. Setting Up AWS RDS

1. **Create an RDS Instance**:
   - Open the **RDS Console** and click **Create database**.
   - Select the database engine (e.g., MySQL, PostgreSQL).
   - Configure the instance settings, including security groups and public accessibility.

2. **Obtain the Database Endpoint**:
   - Note the endpoint and port of your RDS instance.
   - Use this information in your Lambda functions for database connectivity.

3. **Ensure Connectivity**:
   - Update the RDS security group to allow access from the Lambda's VPC or specific IP ranges.

---

## 3. Setting Up Lambda Functions

### 3.1 Standard Lambda Functions
1. **Add Configuration Information**:
   - For Lambda functions (excluding `pokefantasia_compute_typeid`), configure the `pokefantasia-config.ini` file with AWS-specific details.
   
2. **Deploy the Functions**:
   - Open the **Lambda Console** and create functions as needed.
   - Upload the code either as a `.zip` file or use the editor.

3. **Add Lambda Layers**:
   - Attach the necessary Lambda layers for each function in the **Configuration** tab.

---

### 3.2 Lambda Functions with ECR

#### Step 1: Create an ECR Repository
1. Open the **ECR Console** and click **Create repository**.
2. Note the repository URI for future reference.

#### Step 2: Configure Files for Deployment
1. Update the `pokefantasia-config.ini` file with AWS configuration details.
2. Modify the bash script to include the repository URI.

#### Step 3: Build and Push the Docker Image
1. Run the bash script to:
   - Build the Docker image.
   - Push it to the specified ECR repository.

---

## 4. Testing and Debugging

1. **Test Lambda Functions**:
   - Use the AWS Console or CLI to invoke functions and verify their behavior.
   - Confirm database connectivity and expected results.

2. **Monitor and Debug**:
   - Check logs in **CloudWatch Logs** to troubleshoot any issues.
   - Adjust IAM roles or security group configurations if permissions-related errors occur.

---

## Notes
- Clean up unused resources to minimize AWS costs.
- Maintain separate environments (e.g., dev, staging, prod) for organized deployments.

---

With these steps, your serverless architecture for Pokefantasia should be up and running smoothly. Happy coding!