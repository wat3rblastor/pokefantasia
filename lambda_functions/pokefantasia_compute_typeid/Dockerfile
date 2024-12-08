# Use the official AWS Lambda Python 3.10 base image
FROM public.ecr.aws/lambda/python:3.10-x86_64

RUN pip install --upgrade pip

# Install the required Python packages
RUN pip install --no-cache-dir \
    numpy==1.26.4 \
    onnxruntime \
    Pillow==11.0.0 \
    pymysql \
    boto3 \
    configparser

# Copy your application code and config files into the container
# Adjust filenames as necessary if your main code file differs.
COPY --chmod=755 lambda_function.py datatier.py pokefantasia-config.ini ./

RUN chmod 777 /tmp

# Set the CMD to your handler (filename.function_name)
CMD [ "lambda_function.lambda_handler" ]