docker build -f pipelines/Dockerfile_a ./pipelines
docker build -f pipelines/Dockerfile_b ./pipelines
pachctl create repo aaa-input
pachctl create pipeline -f pipelines/pipeline_a
pachctl create pipeline -f pipelines/pipeline_b
pachctl put file aaa-input@master:X/1.txt -f 1.txt
pachctl put file aaa-input@master:X/2.txt -f 2.txt
