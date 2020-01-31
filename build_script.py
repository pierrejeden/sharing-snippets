import docker
import python_pachyderm as pach

docli = docker.from_env()
pacli = pach.Client()

docli.images.build(path='pipelines', dockerfile='Dockerfile_a', tag='aaa-image')
docli.images.build(path='pipelines', dockerfile='Dockerfile_b', tag='bbb-image')
